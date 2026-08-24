"""Network operations: multi-mirror Git cloning, CDN downloads, and repo self-updates."""

import os
import select
import shutil
import subprocess
import sys
import termios
import tempfile
import time
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

from nyxniri.constants import (
    Colors,
    GIT_MIRROR_REGISTRY,
    RAW_MIRROR_TEMPLATES,
)
from nyxniri.core import get_env, log_msg, register_temp_path
from nyxniri.i18n import msg
from nyxniri.tui import prompt_confirm

_GIT_NET = ["-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=15", "-c", "http.connectTimeout=10", "-c", "http.timeout=20"]

@dataclass(frozen=True)
class _ProcessAttempt:
    returncode: int
    stdout: str = ""
    interrupted: bool = False


def _run_cancellable_process(
    command: List[str], capture_stdout: bool = False, show_output: bool = False, **kwargs: Any
) -> _ProcessAttempt:
    """Run a process while allowing Esc/Ctrl+C to cancel only this attempt."""
    if not sys.stdin.isatty():
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE if capture_stdout else (None if show_output else subprocess.DEVNULL),
            stderr=None if show_output else subprocess.DEVNULL,
            text=True,
            **kwargs,
        )
        try:
            stdout, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            return _ProcessAttempt(-1, "")
        return _ProcessAttempt(process.returncode, stdout or "")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE if capture_stdout else (None if show_output else subprocess.DEVNULL),
        stderr=None if show_output else subprocess.DEVNULL,
        text=True,
        **kwargs,
    )
    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    interrupted = False
    try:
        tty.setraw(fd)
        while process.poll() is None:
            ready, _, _ = select.select([fd], [], [], 0.1)
            if not ready:
                continue
            key = os.read(fd, 1)
            if key == b"\x1b":
                sequence_ready, _, _ = select.select([fd], [], [], 0.05)
                if sequence_ready:
                    os.read(fd, 31)
                    continue
            if key in (b"\x1b", b"\x03"):
                interrupted = True
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
    stdout, _ = process.communicate()
    return _ProcessAttempt(process.returncode, stdout or "", interrupted)


def _with_git_progress(command: List[str]) -> Tuple[List[str], bool]:
    """Force native Git progress only when stderr is attached to a terminal."""
    show_progress = sys.stderr.isatty()
    if not show_progress:
        return command, False
    # Locate the git subcommand (first positional token after git and its
    # value-taking top-level options like -c / -C / --git-dir / --work-tree / --namespace).
    # Inserting --progress before the subcommand would feed it to the preceding
    # value-taking option (e.g. as the -c key), which git rejects.
    value_opts = {"-c", "-C", "--git-dir", "--work-tree", "--namespace"}
    i = 1  # skip "git"
    while i < len(command):
        tok = command[i]
        if tok == "--":
            i += 1
            break
        if tok.startswith("-"):
            i += 2 if tok in value_opts else 1
            continue
        break
    sub_idx = i
    if sub_idx >= len(command):
        return [*command, "--progress"], True
    return [*command[:sub_idx + 1], "--progress", *command[sub_idx + 1:]], True


def _run_git_transfer(command: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a Git network command with native TTY progress and quiet automation output."""
    progress_command, show_progress = _with_git_progress(command)
    return subprocess.run(
        progress_command,
        capture_output=not show_progress,
        text=True,
        check=False,
        **kwargs,
    )


def git_clone_timeout(url: str, target_dir: Path, cancellable: bool = False) -> bool:
    """Perform a shallow clone with strict network timeouts and non-interactive prompts."""
    try:
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
        command = [
            "git",
            "clone",
            "-c",
            "http.lowSpeedTime=15",
            "-c",
            "http.lowSpeedLimit=1000",
            "-c",
            "http.connectTimeout=10",
            "-c",
            "http.timeout=20",
            "--depth",
            "1",
            url,
            str(target_dir),
        ]
        command, show_progress = _with_git_progress(command)
        if cancellable:
            attempt = _run_cancellable_process(command, show_output=show_progress, env=env)
            return not attempt.interrupted and attempt.returncode == 0
        res = subprocess.run(
            command,
            capture_output=not show_progress,
            text=True,
            env=env,
            check=False,
        )
        return res.returncode == 0
    except Exception as e:
        log_msg("WARN", f"git_clone_timeout exception: {e}")
        return False


def clone_repo_with_fallback(target_dir: Path, mirrors: Optional[List[Tuple[str, str]]] = None) -> bool:
    """Clone repository attempting each configured mirror in order."""
    if mirrors is None:
        mirrors = GIT_MIRROR_REGISTRY

    log_msg("INFO", "Starting Git clone with fallback mirrors")
    sys.stderr.write(msg("net_pull_repo") + "\n")

    total = len(mirrors)
    for idx, (tag, url) in enumerate(mirrors, start=1):
        sys.stderr.write(msg("net_pull_node", idx, total, tag) + "\n")
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        if git_clone_timeout(url, target_dir):
            sys.stderr.write(msg("net_pull_node_ok", tag))
            log_msg("INFO", f"Git clone [{tag}] SUCCESS ({url})")
            return True
        else:
            sys.stderr.write(msg("net_pull_node_fail", tag) + "\n")
            log_msg("WARN", f"Git clone [{tag}] FAILED ({url})")

    sys.stderr.write(msg("net_pull_all_fail"))
    log_msg("ERROR", "All Git clone attempts failed")
    return False


def fetch_raw_with_fallback(user_repo: str, branch: str, file_path: str, output_file: Path) -> bool:
    """Download a raw asset via 3-tier mirror fallback (Official -> jsDelivr CDN -> gh-proxy)."""
    log_msg("INFO", f"Fetching raw file: {user_repo}/{file_path} ({branch})")
    sys.stdout.write(msg("net_download_asset", user_repo, file_path) + "\n")
    if sys.stdin.isatty():
        sys.stdout.write(msg("net_download_hint") + "\n")

    total = len(RAW_MIRROR_TEMPLATES)
    for idx, (tag, template) in enumerate(RAW_MIRROR_TEMPLATES, start=1):
        url = (
            template.replace("{USER_REPO}", user_repo)
            .replace("{BRANCH}", branch)
            .replace("{FILE_PATH}", file_path)
        )
        sys.stdout.write(msg("net_download_node", idx, total, tag))
        sys.stdout.flush()

        tmp_fd, tmp_name = tempfile.mkstemp()
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        register_temp_path(tmp_path)

        start_time = time.time()
        try:
            command = [
                "curl",
                "-sfL",
                "--connect-timeout",
                "3",
                "-m",
                "10",
                "-w",
                "%{http_code}",
                "-o",
                str(tmp_path),
                url,
            ]
            attempt = _run_cancellable_process(
                command,
                capture_stdout=True,
                env={**os.environ, "LC_ALL": "C"},
            )
            if attempt.interrupted:
                sys.stdout.write(msg("net_download_interrupted") + "\n")
                log_msg("INFO", f"User skipped raw fetch mirror [{tag}]")
                continue
            http_code = attempt.stdout.strip() or "000"
            duration_ms = int((time.time() - start_time) * 1000)

            if http_code == "200" and tmp_path.stat().st_size > 0:
                # Check for HTML 404 block page
                first_lines = tmp_path.read_text(encoding="utf-8", errors="ignore")[:200].lower()
                if "<html" not in first_lines:
                    sys.stdout.write(msg("net_download_ok", duration_ms) + "\n")
                    log_msg("INFO", f"Downloaded raw file via [{tag}] ({url}) - {duration_ms}ms")
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(tmp_path), str(output_file))
                    sys.stdout.write(msg("net_download_node_ok", tag))
                    return True
            sys.stdout.write(msg("net_download_fail", http_code) + "\n")
        except Exception as e:
            sys.stdout.write(f"{Colors.BOLD_RED}[✗] {e}{Colors.RESET}\n")
        finally:
            tmp_path.unlink(missing_ok=True)

    sys.stdout.write(msg("net_download_all_fail"))
    log_msg("ERROR", f"All raw fetch attempts failed for {user_repo}/{file_path}")
    return False


def safe_git_pull(target_dir: Path) -> Optional[bool]:
    """Pull upstream changes: True=updated, None=skipped, False=failed."""
    if not shutil.which("git"):
        print(msg("git_required"))
        return False

    if not (target_dir / ".git").is_dir():
        log_msg("ERROR", f"Update target is not a Git repository: {target_dir}")
        return False

    run_mode = get_env().run_mode
    env = {**os.environ, "LC_ALL": "C"}
    # Check for uncommitted changes
    res_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if res_status.stdout.strip():
        # Dirty tree
        print(msg("dirty_tree_warn", str(target_dir)))
        if run_mode == "repo":
            print(msg("update_skipped_dev_repo", str(target_dir)))
            log_msg("WARN", f"Skipped update for dirty local repo: {target_dir}")
            return None
        if not sys.stdin.isatty():
            print(msg("update_cancelled_dirty"))
            log_msg("WARN", f"Skipped update for dirty cache (non-interactive): {target_dir}")
            return False
        if not prompt_confirm("dirty_tree_confirm", "n"):
            print(msg("update_cancelled_dirty"))
            return None
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=target_dir, check=False, env=env)
        subprocess.run(["git", "clean", "-fd"], cwd=target_dir, check=False, env=env)

    # Fetch & pull
    sys.stdout.write(msg("checking_updates") + "\n")
    res_pull = _run_git_transfer(
        ["git", *_GIT_NET, "pull", "--ff-only"],
        cwd=target_dir,
        env=env,
    )
    if res_pull.returncode == 0:
        return True

    if run_mode == "repo":
        print(msg("update_skipped_dev_repo", str(target_dir)))
        log_msg("WARN", f"Skipped non-fast-forward update for local repo: {target_dir}")
        return None

    # Fallback to fetch & reset only for the disposable remote cache.
    res_fetch = _run_git_transfer(
        ["git", *_GIT_NET, "fetch", "--depth", "1", "origin", "main"],
        cwd=target_dir,
        env=env,
    )
    if res_fetch.returncode == 0:
        res_reset = subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return res_reset.returncode == 0
    log_msg("ERROR", f"Failed to update repository: {target_dir}")
    return False
