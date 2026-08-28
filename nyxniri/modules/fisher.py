"""fisher plugin manager — auto-installed by deploy, uninstallable as a module.

Unlike fcitx/greeter/gtk (opt-in modules), fisher is auto-installed by every
``nyxniri install`` (it manages the shell plugins the fish config ships). It is
promoted to a first-class module so ``nyxniri fisher status|uninstall`` works
and the uninstall module tuple is uniform (§8.6: all module uninstallers in
modules/, none imported back from deploy).
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from nyxniri.core import get_env, log_msg, register_temp_path
from nyxniri.i18n import msg, text
from nyxniri.network import fetch_raw_with_fallback


def fisher_installed() -> bool:
    """True if the fisher loader file exists (~/.config/fish/functions/fisher.fish)."""
    env = get_env()
    return (env.config_dir / "fish" / "functions" / "fisher.fish").is_file()

def fisher_status_label() -> str:
    """Compact status label for menus."""
    return msg("status_enabled") if fisher_installed() else msg("status_not_installed")

def fisher_install() -> bool:
    if not shutil.which("fish"):
        return False
    print(msg("log_check_fisher"))
    log_msg("INFO", "Checking Fisher plugin manager installation")
    fish_check = subprocess.run(
        ["fish", "-c", "functions -q fisher; echo $status"],
        capture_output=True, text=True, check=False, timeout=10,
    )
    if fish_check.returncode == 0 and fish_check.stdout.strip() == "0":
        fish_plugins = get_env().config_dir / "fish" / "fish_plugins"
        need_update = True
        if fish_plugins.is_file():
            state_file = get_env().state_dir / "fish_plugins.mtime"
            current_mtime = str(fish_plugins.stat().st_mtime_ns)
            stored_mtime = ""
            if state_file.is_file():
                try:
                    stored_mtime = state_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass
            need_update = current_mtime != stored_mtime
            if need_update:
                try:
                    state_file.parent.mkdir(parents=True, exist_ok=True)
                    state_file.write_text(current_mtime, encoding="utf-8")
                except Exception:
                    pass
        if need_update:
            log_msg("INFO", "Fisher installed, running update")
            try:
                subprocess.run(["fish", "-c", "fisher update"], check=False, timeout=60)
            except subprocess.TimeoutExpired:
                log_msg("WARN", "Fisher update timed out, skipping")
        else:
            log_msg("INFO", "Fisher installed, fish_plugins unchanged")
        return True

    tfd, tname = tempfile.mkstemp(suffix=".fish")
    os.close(tfd)
    fisher_path = Path(tname)
    register_temp_path(fisher_path)
    msg_install = msg("log_install_fish_plugins")
    msg_skip = msg("log_fisher_update_skipped")
    known_sha256 = os.environ.get("NYXNIRI_FISHER_SHA256", "")
    if fetch_raw_with_fallback("jorgebucaran/fisher", "main", "functions/fisher.fish", fisher_path, expected_sha256=known_sha256 or None):
        fish_code = (
            f"if not functions -q fisher; source '{fisher_path}' && fisher install jorgebucaran/fisher; end; "
            f"if test -f ~/.config/fish/fish_plugins && functions -q fisher; "
            f"echo '{msg_install}'; fisher update || echo '{msg_skip}'; end"
        )
        try:
            subprocess.run(["fish", "-c", fish_code], check=False, timeout=60)
        except subprocess.TimeoutExpired:
            log_msg("WARN", "Fisher bootstrap timed out")
        return True
    print(msg("log_fisher_install_skipped"))
    log_msg("WARN", "Fisher auto-install skipped (network unreachable)")
    return False

def fisher_uninstall() -> bool:
    """Remove fisher and every plugin it installed (§8.4 decision #1: aggressive).

    NyxNiri installed fisher → NyxNiri removes it. fish present: ask fisher to
    ``remove --all`` (it knows its plugins), then drop the loader. fish absent:
    degrade to a direct ``rm -rf`` of fisher.fish + conf.d/ — uninstall often
    happens because the user already left fish, so the host may be gone. §8.6
    """
    env = get_env()
    fish_dir = env.config_dir / "fish"
    fisher_file = fish_dir / "functions" / "fisher.fish"
    conf_d = fish_dir / "conf.d"

    if shutil.which("fish"):
        check = subprocess.run(
            ["fish", "-c", "functions -q fisher; echo $status"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        if check.returncode == 0 and check.stdout.strip() == "0":
            subprocess.run(
                ["fish", "-c", "fisher remove --all"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
            )
            log_msg("INFO", "fisher remove --all ran")
        # fisher not installed → no managed plugins to remove; just drop the loader.
    else:
        # Host gone — fisher can't enumerate plugins. Nuke its footprint directly.
        if conf_d.is_dir():
            shutil.rmtree(conf_d, ignore_errors=True)
            log_msg("INFO", "Removed fish conf.d/ (fisher fallback, fish absent)")
    fisher_file.unlink(missing_ok=True)
    log_msg("INFO", "Uninstalled fisher + fish plugins")
    return True

def fisher_status() -> None:
    """Print fisher install state."""
    print(msg("fisher_status_title"))
    if fisher_installed():
        print(msg("doctor_ok", text("fisher: 已安装", "fisher: installed")))
    else:
        print(msg("doctor_warn", text("fisher: 未安装", "fisher: not installed")))
