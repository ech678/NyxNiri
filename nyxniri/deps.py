"""System dependency management, package detection, AUR bootstrap, and optional software installer."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxniri.constants import AUR_DEPS, CORE_DEPS, OPTIONAL_APPS
from nyxniri.core import log_msg, register_temp_path
from nyxniri.i18n import msg
from nyxniri.network import git_clone_timeout
from nyxniri.tui import CheckboxEntry, CheckboxList, pad_display, prompt_confirm

def is_dep_installed(cmd: str) -> bool:
    """Accurately check whether a specific software or font dependency is installed on the system."""
    env = {**os.environ, "LC_ALL": "C"}

    # 1. Pacman package database (most authoritative on Arch)
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", cmd], capture_output=True, text=True, check=False, env=env)
        if res.returncode == 0:
            return True

    # 2. Specific runtime / font / tool checks
    if cmd == "inotify-tools":
        return shutil.which("inotifywait") is not None
    elif cmd == "mission-center":
        return shutil.which("missioncenter") is not None
    elif cmd == "python-gobject":
        res = subprocess.run([sys.executable, "-c", "import gi"], capture_output=True, check=False)
        return res.returncode == 0
    elif cmd == "gtk-layer-shell":
        res = subprocess.run([sys.executable, "-c", "import gi; gi.require_version('GtkLayerShell', '0.1')"], capture_output=True, check=False)
        return res.returncode == 0
    elif cmd == "ttf-jetbrains-mono":
        if shutil.which("fc-list"):
            res = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False, env=env)
            return "jetbrains mono" in res.stdout.lower()
    elif cmd == "ttf-jetbrains-mono-nerd":
        if shutil.which("fc-list"):
            res = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False, env=env)
            return bool(re.search(r"jetbrains.*nerd", res.stdout, re.IGNORECASE))
    elif cmd == "noto-fonts-cjk":
        if shutil.which("fc-list"):
            res = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False, env=env)
            return bool(re.search(r"noto.*cjk", res.stdout, re.IGNORECASE))

    # 3. Fallback binary lookup
    return shutil.which(cmd) is not None

def check_all_deps() -> Dict[str, bool]:
    """Check status of all core dependencies."""
    return {dep: is_dep_installed(dep) for dep in CORE_DEPS}

def get_missing_deps() -> List[str]:
    """Retrieve list of missing core dependencies."""
    status_map = check_all_deps()
    return [dep for dep, installed in status_map.items() if not installed]

def aur_helper_usable() -> Optional[str]:
    """Return name of a functioning AUR helper (paru or yay) after verifying binary execution."""
    for helper in ("paru", "yay"):
        if shutil.which(helper):
            try:
                res = subprocess.run([helper, "--version"], capture_output=True, check=False)
                if res.returncode == 0:
                    return helper
            except Exception:
                pass
    return None

def get_preferred_pkg_manager() -> List[str]:
    """Resolve preferred package manager (AUR helper if available, otherwise ['sudo', 'pacman'])."""
    helper = aur_helper_usable()
    if helper:
        return [helper]
    return ["sudo", "pacman"]

def ensure_aur_helper() -> Optional[str]:
    """Bootstrap an AUR helper (paru) if none is available, compiling from source if needed."""
    helper = aur_helper_usable()
    if helper:
        return helper

    if not prompt_confirm("aur_bootstrap_prompt", "y"):
        print(msg("aur_bootstrap_skip"))
        return None

    print(msg("aur_bootstrap_start"))
    if not shutil.which("pacman"):
        print(msg("aur_bootstrap_failed"))
        return None

    # Remove stale paru-bin if conflicting
    env = {**os.environ, "LC_ALL": "C"}
    for stale in ("paru-bin", "paru-bin-debug"):
        res = subprocess.run(["pacman", "-Qq", stale], capture_output=True, check=False, env=env)
        if res.returncode == 0:
            print(msg("aur_bootstrap_cleanup"))
            subprocess.run(["sudo", "pacman", "-Rdd", "--noconfirm", stale], check=False)

    # 1. Try official repo package
    res_si = subprocess.run(["pacman", "-Si", "paru"], capture_output=True, check=False, env=env)
    if res_si.returncode == 0:
        print(msg("aur_bootstrap_repo"))
        subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", "paru"], check=False)
        helper = aur_helper_usable()
        if helper:
            print(msg("aur_bootstrap_ok"))
            return helper

    # 2. Source build from AUR
    subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", "base-devel", "git"], check=False)
    print(msg("aur_bootstrap_source"))

    build_dir = Path(tempfile.mkdtemp())
    register_temp_path(build_dir)
    clone_ok = git_clone_timeout(
        "https://aur.archlinux.org/paru.git",
        build_dir / "paru",
        cancellable=sys.stdin.isatty(),
    )
    if clone_ok:
        makepkg_res = subprocess.run(["makepkg", "-si", "--noconfirm"], cwd=build_dir / "paru", check=False)
        helper = aur_helper_usable()
        if makepkg_res.returncode == 0 and helper:
            print(msg("aur_bootstrap_ok"))
            return helper

    print(msg("aur_bootstrap_failed"))
    return None

def check_mpvpaper_leak() -> None:
    """Check mpvpaper version for the OpenGL memory leak bug (< 1.9) and offer upgrade."""
    if not shutil.which("mpvpaper"):
        return
    try:
        res = subprocess.run(["mpvpaper", "--version"], capture_output=True, text=True, check=False)
        out = res.stdout or res.stderr
        m = re.search(r"mpvpaper\s+v?([0-9]+(?:\.[0-9]+)+)", out)
        if m:
            ver_str = m.group(1)
            try:
                parts = tuple(int(p) for p in ver_str.split("."))
                if parts < (1, 9):
                    print(msg("mpvpaper_leak_warn", ver_str))
                    if sys.stdin.isatty():
                        from nyxniri.tui import prompt_confirm
                        if prompt_confirm("mpvpaper_leak_upgrade_prompt", "n"):
                            print(msg("mpvpaper_upgrading"))
                            helper = aur_helper_usable()
                            if helper:
                                subprocess.run([helper, "-S", "--needed", "--noconfirm", "mpvpaper-git"], check=False)
                            else:
                                helper = ensure_aur_helper()
                                if helper:
                                    subprocess.run([helper, "-S", "--needed", "--noconfirm", "mpvpaper-git"], check=False)
                                else:
                                    print(msg("mpvpaper_upgrade_skip"))
                        else:
                            print(msg("mpvpaper_upgrade_skip"))
                    else:
                        print(msg("mpvpaper_upgrade_skip"))
                else:
                    print(msg("mpvpaper_version_ok", ver_str))
            except ValueError:
                pass
    except Exception:
        pass

def install_selected_deps(selected_deps: List[str]) -> bool:
    """Install selected packages using pacman or AUR helper."""
    if not selected_deps:
        return True

    repo_pkgs = [pkg for pkg in selected_deps if pkg not in AUR_DEPS]
    aur_pkgs = [pkg for pkg in selected_deps if pkg in AUR_DEPS]

    if repo_pkgs:
        cmd = ["sudo", "pacman", "-S", "--needed", "--noconfirm", *repo_pkgs]
        print(msg("installing_official_packages", " ".join(repo_pkgs)))
        res = subprocess.run(cmd, check=False)
        if res.returncode != 0:
            print(msg("log_official_pkgs_partial_fail"))

    if aur_pkgs:
        helper = ensure_aur_helper()
        if helper:
            cmd = [helper, "-S", "--needed", "--noconfirm", *aur_pkgs]
            print(msg("installing_aur_packages", " ".join(aur_pkgs)))
            res = subprocess.run(cmd, check=False)
            if res.returncode != 0:
                print(msg("log_aur_pkgs_partial_fail"))
        else:
            print(msg("aur_skip", ", ".join(aur_pkgs)))

    if "mpvpaper" in selected_deps:
        check_mpvpaper_leak()

    return True

def run_dep_menu_loop() -> None:
    """Open interactive checkbox list for core dependencies."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    status_map = check_all_deps()
    entries = []
    for dep in CORE_DEPS:
        is_inst = status_map[dep]
        status_tag = msg("installed") if is_inst else msg("missing")
        label = f"{pad_display(dep, 24)} {status_tag}"
        entries.append(CheckboxEntry(key=dep, label=label, checked=not is_inst))

    chk = CheckboxList("dep_menu_title", entries, hint_key="dep_menu_hint")
    chosen = chk.run()
    if chosen:
        print(msg("installing_selected"))
        install_selected_deps(chosen)

def run_optional_apps_menu_loop() -> None:
    """Open interactive checkbox list for recommended applications."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    entries = []
    for app in OPTIONAL_APPS:
        is_inst = is_dep_installed(app)
        status_tag = msg("installed") if is_inst else msg("missing")
        app_label = msg(f"app_{app.replace('-', '_')}")
        label = f"{pad_display(app_label, 32)} {status_tag}"
        entries.append(CheckboxEntry(key=app, label=label, checked=not is_inst))

    chk = CheckboxList("opt_apps_menu_title", entries, hint_key="opt_apps_menu_hint")
    chosen = chk.run()
    if chosen:
        print(msg("installing_selected_apps"))
        install_selected_deps(chosen)
        from nyxniri.fcitx import fcitx5_installed, fcitx_install
        if "fcitx5-rime" in chosen and fcitx5_installed():
            print(msg("fcitx_auto_deploy_after_install"))
            fcitx_install()
        print(msg("opt_apps_install_done"))
    else:
        print(msg("opt_apps_none_selected"))
