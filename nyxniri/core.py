"""Core runtime infrastructure: paths, locking, logging, traps, and version detection."""

import atexit
import datetime
import fcntl
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

from nyxniri.constants import (
    ASSETS_DIR_NAME,
    CLI_CMD,
    CONFIG_DIR_NAME,
    PROJECT_NAME,
)

# --- Temporary Paths Registry ---
_CLEANUP_TEMP_PATHS: set[Path] = set()

def register_temp_path(path: Path | str) -> None:
    """Register a temporary path to be swept on process exit."""
    if path:
        _CLEANUP_TEMP_PATHS.add(Path(path))

def cleanup_temp_paths() -> None:
    """Remove all registered temporary files and directories."""
    for p in list(_CLEANUP_TEMP_PATHS):
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists() or p.is_symlink():
                p.unlink(missing_ok=True)
        except Exception:
            pass
    _CLEANUP_TEMP_PATHS.clear()

atexit.register(cleanup_temp_paths)

# --- Path Resolution & Environment Context ---
class Environment:
    def __init__(self):
        self.home = Path(os.environ.get("HOME", str(Path.home())))
        self.state_dir = Path(os.environ.get("XDG_STATE_HOME", str(self.home / ".local/state"))) / PROJECT_NAME
        self.cache_dir = self.home / ".cache" / PROJECT_NAME
        self.config_dir = self.home / ".config"

        # Discover execution location & mode
        current_file = Path(__file__).resolve()
        pkg_dir = current_file.parent
        root_dir = pkg_dir.parent

        if root_dir.resolve() == self.cache_dir.resolve():
            self.run_mode = "standalone"
            self.mode_label = "Remote Cache"
            self.repo_dir = self.cache_dir
        elif (root_dir / CONFIG_DIR_NAME).is_dir() and (root_dir / ASSETS_DIR_NAME).is_dir():
            self.run_mode = "repo"
            self.mode_label = "Local Path"
            self.repo_dir = root_dir
        else:
            self.run_mode = "standalone"
            self.mode_label = "Remote Cache"
            self.repo_dir = self.cache_dir

        self.configs_src = self.repo_dir / CONFIG_DIR_NAME
        self.assets_src = self.repo_dir / ASSETS_DIR_NAME
        self.version = get_version(self.repo_dir)

_ENV: Optional[Environment] = None

def get_env() -> Environment:
    """Retrieve or initialize the global Environment context."""
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV

_PICS_DIR_CACHE: Optional[Path] = None

def get_pics_dir() -> Path:
    global _PICS_DIR_CACHE
    if _PICS_DIR_CACHE is not None:
        return _PICS_DIR_CACHE
    home = get_env().home
    try:
        res = subprocess.run(
            ["xdg-user-dir", "PICTURES"],
            capture_output=True, text=True, check=False,
            env={**os.environ, "LC_ALL": "C"}
        )
        d = res.stdout.strip()
        if d and d != str(home):
            _PICS_DIR_CACHE = Path(d)
            return _PICS_DIR_CACHE
    except Exception:
        pass
    _PICS_DIR_CACHE = home / "Pictures"
    return _PICS_DIR_CACHE

# --- Dynamic Version Extractor ---
_VERSION_CACHE: str = ""

def get_version(target_dir: Path) -> str:
    global _VERSION_CACHE
    if _VERSION_CACHE:
        return _VERSION_CACHE
    changelog = target_dir / "CHANGELOG.md"
    if changelog.is_file():
        try:
            content = changelog.read_text(encoding="utf-8")
            for candidate in re.findall(r"^##\s+\[([^\]]+)\]", content, re.MULTILINE):
                if candidate.lower() != "unreleased":
                    _VERSION_CACHE = candidate
                    return _VERSION_CACHE
        except Exception:
            pass
    if (target_dir / ".git").is_dir():
        try:
            res = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=target_dir, capture_output=True, text=True, check=False,
                env={**os.environ, "LC_ALL": "C"}
            )
            v = res.stdout.strip()
            if v:
                _VERSION_CACHE = v
                return _VERSION_CACHE
        except Exception:
            pass
    _VERSION_CACHE = "v3.0.0"
    return _VERSION_CACHE

# --- Single-Instance Lock (fcntl.flock — auto-releases on process death) ---
_LOCK_FILE: Optional[Path] = None
_LOCK_FD: Optional[int] = None

def acquire_lock() -> None:
    """Acquire single-instance lock via fcntl.flock.

    flock is kernel-level and auto-releases when the process exits (even on
    SIGKILL), so there is no stale-lock healing to do and no check-then-write
    race. A PID is still written to the file for diagnostics only.
    """
    global _LOCK_FILE, _LOCK_FD
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE = env.state_dir / f"{CLI_CMD}.lock"
    try:
        _LOCK_FD = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        # Another instance holds the lock — surface its PID if we can read it
        pid = "unknown"
        try:
            content = _LOCK_FILE.read_text().strip()
            if content.isdigit():
                pid = content
        except Exception:
            pass
        from nyxniri.i18n import msg
        print(msg("err_already_running", pid), file=sys.stderr)
        sys.exit(1)
    # Best-effort PID write for diagnostics (the lock itself is the source of truth)
    try:
        os.ftruncate(_LOCK_FD, 0)
        os.write(_LOCK_FD, str(os.getpid()).encode())
    except Exception:
        pass

def release_lock() -> None:
    """Release the single-instance lock and remove the lock file."""
    global _LOCK_FD, _LOCK_FILE
    if _LOCK_FD is not None:
        try:
            fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
            os.close(_LOCK_FD)
        except Exception:
            pass
        _LOCK_FD = None
    if _LOCK_FILE:
        try:
            _LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

atexit.register(release_lock)

# --- Rolling Log Engine ---
_LOG_FILE: Optional[Path] = None
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def init_logger() -> None:
    """Initialize state directory and truncate log to the last 800 lines."""
    global _LOG_FILE
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = env.state_dir / "install.log"

    if _LOG_FILE.is_file():
        try:
            lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > 800:
                _LOG_FILE.write_text("\n".join(lines[-800:]) + "\n", encoding="utf-8")
        except Exception:
            pass

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"{now} [INFO] {PROJECT_NAME} Session Started ({env.version}) [mode: {env.mode_label}]\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception:
        pass

def log_msg(level: str, message: str) -> None:
    """Write timestamped, clean message (stripped of ANSI codes) to log file."""
    if _LOG_FILE is None:
        return
    clean_text = ANSI_ESCAPE_RE.sub("", message)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} [{level}] {clean_text}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

# --- CLI Binary Symlink ---
def ensure_nyxniri_symlink() -> None:
    """Ensure ~/.local/bin/nyxniri points to install.sh."""
    env = get_env()
    bin_dir = env.home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_bin = bin_dir / CLI_CMD

    root_installer = env.repo_dir / "install.sh"
    if not root_installer.is_file():
        if (env.cache_dir / "install.sh").is_file():
            root_installer = env.cache_dir / "install.sh"
        else:
            return

    try:
        if not target_bin.is_symlink() or target_bin.resolve() != root_installer.resolve():
            target_bin.unlink(missing_ok=True)
            target_bin.symlink_to(root_installer)
        root_installer.chmod(0o755)
    except Exception:
        pass
