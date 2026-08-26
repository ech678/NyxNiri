"""System dependency management, package detection, AUR bootstrap, and optional software installer."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxniri.constants import (
    AUR_DEPS,
    CORE_DEPS,
    FEDORA_COPR_REPOS,
    FEDORA_MIN_VERSION,
    FEDORA_PKG_MAP,
    FEDORA_RPM_FUSION_REPOS,
    FEDORA_SKIP_APPS,
    OPTIONAL_APPS,
)
from nyxniri.core import log_msg, register_temp_path
from nyxniri.i18n import msg
from nyxniri.network import git_clone_timeout
from nyxniri.tui import CheckboxEntry, CheckboxList, pad_display, prompt_confirm


# --- Distro Detection ---

_OS_RELEASE_CACHE: Optional[Dict[str, str]] = None

def _read_os_release() -> Dict[str, str]:
    """Parse /etc/os-release once and cache the result."""
    global _OS_RELEASE_CACHE
    if _OS_RELEASE_CACHE is not None:
        return _OS_RELEASE_CACHE
    data: Dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip().strip('"\'')
    except Exception:
        pass
    _OS_RELEASE_CACHE = data
    return data

def detect_distro() -> str:
    """Return 'fedora', 'arch', or 'unknown' based on /etc/os-release."""
    info = _read_os_release()
    distro_id = info.get("ID", "").lower()
    likes = info.get("ID_LIKE", "").lower().split()
    if distro_id == "fedora" or "fedora" in likes:
        return "fedora"
    if distro_id in ("arch", "cachyos") or "arch" in likes:
        return "arch"
    return "unknown"

def is_fedora() -> bool:
    """True on Fedora (or derivatives whose ID_LIKE contains fedora)."""
    return detect_distro() == "fedora"

def is_arch() -> bool:
    """True on Arch / CachyOS (or derivatives whose ID_LIKE contains arch)."""
    return detect_distro() == "arch"

def fedora_version() -> Optional[int]:
    """Return Fedora major version as int, or None if not on Fedora / unparseable."""
    info = _read_os_release()
    ver = info.get("VERSION_ID", "")
    if not ver:
        return None
    try:
        return int(ver.split(".")[0])
    except ValueError:
        return None


def is_dep_installed(cmd: str) -> bool:
    """Accurately check whether a specific software or font dependency is installed on the system."""
    env = {**os.environ, "LC_ALL": "C"}

    # 1. Native package database (pacman on Arch, rpm on Fedora)
    if is_arch() and shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", cmd], capture_output=True, text=True, check=False, env=env)
        if res.returncode == 0:
            return True
    elif is_fedora() and shutil.which("rpm"):
        # On Fedora, the Arch key must be translated to one or more rpm
        # package names. If any of the mapped names is installed, treat the
        # dependency as satisfied.
        fedora_pkgs = FEDORA_PKG_MAP.get(cmd, {}).get("pkgs", [cmd])
        for pkg in fedora_pkgs:
            res = subprocess.run(["rpm", "-q", pkg], capture_output=True, text=True, check=False, env=env)
            if res.returncode == 0:
                return True

    # 2. Specific runtime / font / tool checks
    if cmd == "inotify-tools":
        return shutil.which("inotifywait") is not None
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
    elif cmd == "nvidia-driver":
        # Check if NVIDIA kernel module is loaded or akmod-nvidia is installed (Fedora).
        if is_fedora() and shutil.which("rpm"):
            res = subprocess.run(["rpm", "-q", "akmod-nvidia"], capture_output=True, check=False, env=env)
            if res.returncode == 0:
                return True
        # Check if nvidia kernel module is available on any distro.
        if shutil.which("modinfo"):
            res = subprocess.run(["modinfo", "-F", "version", "nvidia"],
                                 capture_output=True, text=True, check=False, env=env)
            if res.returncode == 0 and res.stdout.strip():
                return True
        return False

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
    # AUR does not exist on Fedora; short-circuit so the Arch bootstrap path
    # never runs there.
    if is_fedora():
        return None
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
    """Resolve preferred package manager (AUR helper, otherwise sudo + native PM)."""
    if is_fedora():
        return ["sudo", "dnf"]
    helper = aur_helper_usable()
    if helper:
        return [helper]
    return ["sudo", "pacman"]

def ensure_aur_helper() -> Optional[str]:
    """Bootstrap an AUR helper (paru) if none is available, compiling from source if needed."""
    # No AUR on Fedora; callers that fall through here should treat the
    # return value as "no helper" and skip AUR-only packages.
    if is_fedora():
        return None

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
        # Repo paru installed but not usable — remove before source build to avoid conflicts
        subprocess.run(["sudo", "pacman", "-Rdd", "--noconfirm", "paru"], check=False)

    # 2. Source build from AUR
    res_base = subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", "base-devel", "git"], check=False)
    if res_base.returncode != 0:
        print(msg("aur_bootstrap_failed"))
        return None
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
    # On Fedora, mpvpaper is built from source by the user; there's no pacman
    # metadata to query and the user controls the version. Skip the check.
    if is_fedora():
        return
    if not shutil.which("pacman"):
        return
    env = {**os.environ, "LC_ALL": "C"}

    # Already on git version?
    res_git = subprocess.run(["pacman", "-Qi", "mpvpaper-git"], capture_output=True, text=True, check=False, env=env)
    if res_git.returncode == 0:
        git_ver = ""
        for line in res_git.stdout.splitlines():
            if line.startswith("Version"):
                git_ver = line.split(":", 1)[1].strip()
                break
        print(msg("mpvpaper_version_ok", f"git ({git_ver or 'unknown'})"))
        return

    if not shutil.which("mpvpaper"):
        return

    print(msg("checking_mpvpaper"))
    res = subprocess.run(["pacman", "-Qi", "mpvpaper"], capture_output=True, text=True, check=False, env=env)
    version = ""
    for line in res.stdout.splitlines():
        if line.startswith("Version"):
            version = line.split(":", 1)[1].strip()
            break
    if not version:
        return

    # Strip epoch and pkgrel: "1:1.8.2-3" → "1.8.2"
    clean_ver = re.sub(r'^[0-9]+:', '', version)
    clean_ver = re.sub(r'-.*$', '', clean_ver)
    clean_ver = re.sub(r'[^0-9.]', '', clean_ver)
    parts = clean_ver.split(".")
    try:
        major = int(parts[0]) if parts and parts[0].isdigit() else 0
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    except ValueError:
        return

    if major > 1 or (major == 1 and minor >= 9):
        print(msg("mpvpaper_version_ok", version))
    else:
        print(msg("mpvpaper_leak_warn", version))
        if prompt_confirm("mpvpaper_upgrade_prompt", "n"):
            mgr = aur_helper_usable()
            if not mgr:
                mgr = ensure_aur_helper()
            if mgr:
                res_inst = subprocess.run([mgr, "-S", "--noconfirm", "mpvpaper-git"], check=False)
                if res_inst.returncode == 0:
                    print(msg("mpvpaper_upgrade_done"))
                else:
                    print(msg("err_mpvpaper_git_failed"))
            else:
                print(msg("mpvpaper_upgrade_skip"))
        else:
            print(msg("mpvpaper_upgrade_skip"))


# --- Fedora: COPR enable + source builds for starship / mpvpaper / ffmpeg ---

def enable_fedora_copr_repos() -> bool:
    """Auto-enable all configured COPR repos on Fedora via `dnf copr`."""
    if not is_fedora() or not shutil.which("dnf"):
        return False
    for _name, copr_id in FEDORA_COPR_REPOS:
        subprocess.run(["sudo", "dnf", "copr", "enable", "-y", copr_id], check=False)
    return True

def enable_rpmfusion_repos() -> bool:
    """Enable RPM Fusion free + nonfree repos on Fedora (provides NVIDIA drivers)."""
    if not is_fedora() or not shutil.which("dnf"):
        return False
    # Check if rpmfusion-free-release is already installed.
    env = {**os.environ, "LC_ALL": "C"}
    res = subprocess.run(["rpm", "-q", "rpmfusion-free-release"], capture_output=True, check=False, env=env)
    if res.returncode == 0:
        return True  # already enabled
    # Install both free and nonfree release RPMs in one shot.
    pkgs = " ".join(FEDORA_RPM_FUSION_REPOS)
    print(msg("rpmfusion_enabling"))
    res = subprocess.run(f"sudo dnf -y install {pkgs}", shell=True, check=False)
    return res.returncode == 0

def build_nvidia_driver() -> bool:
    """Install NVIDIA proprietary driver on Fedora via RPM Fusion + akmod-nvidia.

    Flow: RPM Fusion repo → akmod-nvidia (driver) → xorg-x11-drv-nvidia-cuda (CUDA/optional)
    Then wait briefly for akmods to build the kernel module.
    """
    print(msg("building_from_source", "nvidia driver"))
    if not enable_rpmfusion_repos():
        print(msg("build_tool_missing", "rpmfusion", "rpmfusion-free-release rpmfusion-nonfree-release"))
        return False

    # Remove nouveau first to avoid conflicts (safe on Fedora Workstation).
    subprocess.run(["sudo", "dnf", "-y", "remove", "xorg-x11-drv-nouveau"], check=False)

    # Install akmod-nvidia (the driver itself, auto-rebuilds on kernel updates).
    print(msg("installing_official_packages", "akmod-nvidia"))
    res = subprocess.run(["sudo", "dnf", "-y", "install", "akmod-nvidia"], check=False)
    if res.returncode != 0:
        print(msg("build_failed_manual", "nvidia driver"))
        return False

    # Optional CUDA + nvidia-smi (NVENC/NVDEC support).
    # Use --setopt=install_weak_deps=False to skip weak deps we don't need.
    subprocess.run(["sudo", "dnf", "-y", "install", "xorg-x11-drv-nvidia-cuda"], check=False)

    # Wait for akmods to finish building the kernel module (poll up to ~15 min).
    print(msg("nvidia_waiting_build"))
    env = {**os.environ, "LC_ALL": "C"}
    import time
    for _ in range(90):  # 90 * 10s = 15 min max
        mod = subprocess.run(["modinfo", "-F", "version", "nvidia"],
                             capture_output=True, text=True, check=False, env=env)
        if mod.returncode == 0 and mod.stdout.strip():
            print(msg("nvidia_build_ready", mod.stdout.strip()))
            return True
        time.sleep(10)
    # Module didn't build in time — still report success so user can reboot later.
    print(msg("nvidia_build_timeout"))
    return True

def _run_build(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> bool:
    """Run a build command, streaming output to the terminal if interactive."""
    res = subprocess.run(cmd, cwd=cwd, env=env, check=False)
    return res.returncode == 0

def build_starship() -> bool:
    """Build and install starship from GitHub via cargo install."""
    print(msg("building_from_source", "starship"))
    cargo_bin = shutil.which("cargo")
    if not cargo_bin:
        # Install Rust via rustup (official installer, no sudo needed, cross-distro).
        print(msg("build_tool_missing", "cargo", "rustup"))
        cargo_home = Path.home() / ".cargo"
        cargo_bin_path = cargo_home / "bin" / "cargo"
        if not cargo_bin_path.exists():
            res = subprocess.run(
                ["bash", "-c",
                 "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"],
                check=False,
            )
            if res.returncode != 0:
                print(msg("build_tool_missing", "cargo", "rustup"))
                return False
        cargo_bin = str(cargo_bin_path)

    # Ensure ~/.cargo/bin is on PATH for this subprocess.
    env = os.environ.copy()
    cargo_bin_dir = str(Path(cargo_bin).parent)
    if cargo_bin_dir not in env.get("PATH", ""):
        env["PATH"] = f"{cargo_bin_dir}:{env.get('PATH', '')}"

    # Install to user-level ~/.cargo/bin first (no sudo needed for the build).
    starship_src = str(Path.home() / ".cargo" / "bin" / "starship")
    if not Path(starship_src).exists():
        res = subprocess.run([cargo_bin, "install", "starship"],
                             env=env, check=False)
        if res.returncode != 0:
            return False
    # Then sudo-copy to /usr/bin so it's available system-wide.
    return subprocess.run(["sudo", "cp", "-f", starship_src, "/usr/bin/starship"],
                          check=False).returncode == 0

def build_mpvpaper() -> bool:
    """Build and install mpvpaper from GitHub via meson + ninja."""
    print(msg("building_from_source", "mpvpaper"))
    for tool in ("meson", "ninja", "pkg-config", "gcc"):
        if not shutil.which(tool):
            print(msg("build_tool_missing", tool,
                      "meson ninja-build gcc pkgconf-pkg-config"))
            return False
    # Ensure build deps via dnf first.
    res_deps = subprocess.run(["sudo", "dnf", "-y", "install",
                               "meson", "ninja-build", "gcc", "pkgconf-pkg-config",
                               "mpv-devel", "wayland-devel", "wayland-protocols-devel",
                               "libglvnd-devel", "libX11-devel"], check=False)
    if res_deps.returncode != 0:
        print(msg("build_tool_missing", "dnf", "meson ninja-build gcc pkgconf-pkg-config mpv-devel wayland-devel wayland-protocols-devel"))
        return False

    build_dir = Path(tempfile.mkdtemp())
    register_temp_path(build_dir)
    if not git_clone_timeout("https://github.com/GhostNaN/mpvpaper.git",
                             build_dir / "mpvpaper",
                             cancellable=sys.stdin.isatty()):
        print(msg("build_clone_failed", "mpvpaper"))
        return False

    src = build_dir / "mpvpaper"
    if not _run_build(["meson", "setup", "build"], cwd=src):
        return False
    if not _run_build(["ninja", "-C", "build"], cwd=src):
        return False
    return subprocess.run(["sudo", "ninja", "-C", "build", "install"],
                          cwd=src, check=False).returncode == 0

def build_ffmpeg() -> bool:
    """Build and install ffmpeg from source with a minimal GPL config."""
    print(msg("building_from_source", "ffmpeg"))
    for tool in ("gcc", "make", "nasm"):
        if not shutil.which(tool):
            print(msg("build_tool_missing", tool, "gcc make nasm"))
            return False
    res_deps = subprocess.run(["sudo", "dnf", "-y", "install",
                               "gcc", "make", "nasm", "pkgconf-pkg-config",
                               "libX11-devel", "wayland-devel",
                               "libdrm-devel", "zlib-devel", "bzip2-devel",
                               "libva-devel", "libvdpau-devel"], check=False)
    if res_deps.returncode != 0:
        print(msg("build_tool_missing", "dnf", "gcc make nasm pkgconf-pkg-config libX11-devel wayland-devel libdrm-devel zlib-devel bzip2-devel libva-devel libvdpau-devel"))
        return False

    build_dir = Path(tempfile.mkdtemp())
    register_temp_path(build_dir)
    if not git_clone_timeout("https://git.ffmpeg.org/ffmpeg.git",
                             build_dir / "ffmpeg",
                             cancellable=sys.stdin.isatty()):
        # Fallback to the GitHub mirror.
        if not git_clone_timeout("https://github.com/FFmpeg/FFmpeg.git",
                                build_dir / "ffmpeg",
                                cancellable=sys.stdin.isatty()):
            print(msg("build_clone_failed", "ffmpeg"))
            return False

    src = build_dir / "ffmpeg"
    # Minimal config: GPL + shared libs + common hwaccels; disable doc/debug to stay lean.
    if not _run_build([
        "./configure",
        "--prefix=/usr/local",
        "--enable-gpl",
        "--enable-shared",
        "--disable-doc",
        "--disable-debug",
    ], cwd=src):
        return False
    if not _run_build(["make", "-j", str(os.cpu_count() or 4)], cwd=src):
        return False
    return subprocess.run(["sudo", "make", "install"], cwd=src,
                          check=False).returncode == 0

def install_selected_deps(selected_deps: List[str]) -> bool:
    """Install selected packages using pacman/AUR (Arch) or dnf + source builds (Fedora)."""
    if not selected_deps:
        return True

    # --- Fedora branch ---
    if is_fedora():
        # Ensure COPR repos are enabled first (e.g. nerd-fonts).
        enable_fedora_copr_repos()

        # If nvidia-driver is requested, enable RPM Fusion (provides the proprietary driver).
        if "nvidia-driver" in selected_deps:
            enable_rpmfusion_repos()

        dnf_pkgs: List[str] = []
        manual_keys: List[str] = []
        for key in selected_deps:
            desc = FEDORA_PKG_MAP.get(key)
            if not desc:
                # Unknown mapping: fall back to the key itself as a dnf name.
                dnf_pkgs.append(key)
                continue
            method = desc.get("method", "dnf")
            if method == "dnf":
                dnf_pkgs.extend(desc.get("pkgs", []))
            elif method == "manual":
                manual_keys.append(key)
            # flatpak apps are not in CORE_DEPS; ignored here.

        if dnf_pkgs:
            print(msg("installing_official_packages", " ".join(dnf_pkgs)))
            res = subprocess.run(["sudo", "dnf", "-y", "install", *dnf_pkgs], check=False)
            if res.returncode != 0:
                print(msg("log_official_pkgs_partial_fail"))

        for key in manual_keys:
            desc = FEDORA_PKG_MAP.get(key, {})
            build_name = desc.get("build")
            # Resolve the builder by name from this module so that tests can
            # patch build_* functions and have the patch take effect here.
            builder = getattr(sys.modules[__name__], build_name, None) if build_name else None
            if builder and builder():
                continue
            # Build failed or no builder — fall back to dnf if a known pkg exists.
            fallback_pkgs = desc.get("pkgs", [])
            if fallback_pkgs:
                print(msg("build_fallback_dnf", key, " ".join(fallback_pkgs)))
                subprocess.run(["sudo", "dnf", "-y", "install", *fallback_pkgs], check=False)
            else:
                print(msg("build_failed_manual", key))

        # mpvpaper leak check is a no-op on Fedora (built from source).
        if "mpvpaper" in selected_deps or shutil.which("mpvpaper"):
            check_mpvpaper_leak()
        return True

    # --- Arch branch (unchanged) ---
    repo_pkgs = [pkg for pkg in selected_deps if pkg not in AUR_DEPS]
    aur_pkgs = [pkg for pkg in selected_deps if pkg in AUR_DEPS]

    if repo_pkgs:
        pkg_mgr = get_preferred_pkg_manager()
        cmd = [*pkg_mgr, "-S", "--needed", "--noconfirm", *repo_pkgs]
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
            print(msg("aur_helper_required"))

    if "mpvpaper" in selected_deps or shutil.which("mpvpaper"):
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

_OPT_APP_PKG_MAP = {
    "nautilus": {"repo": ["nautilus"], "aur": []},
    "missioncenter": {"repo": ["mission-center"], "aur": []},
    "fcitx5-rime": {"repo": ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"], "aur": ["rime-ice-git"]},
}


def install_optional_apps(selected_apps: List[str]) -> None:
    """Install selected optional apps with correct package name mapping."""
    # --- Fedora branch ---
    if is_fedora():
        dnf_pkgs: List[str] = []
        flatpak_apps: List[str] = []
        manual_keys: List[str] = []
        has_fcitx = False
        for app in selected_apps:
            if app in FEDORA_SKIP_APPS:
                continue
            desc = FEDORA_PKG_MAP.get(app)
            if not desc:
                continue
            method = desc.get("method", "dnf")
            if method == "dnf":
                dnf_pkgs.extend(desc.get("pkgs", []))
            elif method == "flatpak":
                flatpak_id = desc.get("flatpak")
                if flatpak_id:
                    flatpak_apps.append(flatpak_id)
            elif method == "manual":
                manual_keys.append(app)
            if app == "fcitx5-rime":
                has_fcitx = True

        if not dnf_pkgs and not flatpak_apps and not manual_keys:
            print(msg("opt_apps_none_selected"))
            return

        print(msg("installing_selected_apps"))
        if dnf_pkgs:
            subprocess.run(["sudo", "dnf", "-y", "install", *dnf_pkgs], check=False)
        if flatpak_apps:
            if shutil.which("flatpak"):
                for fp in flatpak_apps:
                    subprocess.run(["flatpak", "install", "-y", "flathub", fp], check=False)
            else:
                print(msg("flatpak_missing", " ".join(flatpak_apps)))

        # Run manual builds (e.g. NVIDIA driver via RPM Fusion).
        for key in manual_keys:
            desc = FEDORA_PKG_MAP.get(key, {})
            build_name = desc.get("build")
            builder = getattr(sys.modules[__name__], build_name, None) if build_name else None
            if builder:
                builder()

        if has_fcitx and shutil.which("fcitx5"):
            try:
                from nyxniri.fcitx import fcitx_install
                fcitx_install()
            except Exception:
                pass

        print(msg("opt_apps_install_done"))
        return

    # --- Arch branch (unchanged) ---
    repo_pkgs: List[str] = []
    aur_pkgs: List[str] = []
    has_fcitx = False
    for app in selected_apps:
        mapping = _OPT_APP_PKG_MAP.get(app)
        if not mapping:
            continue
        repo_pkgs.extend(mapping["repo"])
        aur_pkgs.extend(mapping["aur"])
        if app == "fcitx5-rime":
            has_fcitx = True

    if not repo_pkgs and not aur_pkgs:
        print(msg("opt_apps_none_selected"))
        return

    print(msg("installing_selected_apps"))
    pkg_mgr = get_preferred_pkg_manager()

    if repo_pkgs:
        subprocess.run([*pkg_mgr, "-S", "--needed", "--noconfirm", *repo_pkgs], check=False)

    if aur_pkgs:
        helper = aur_helper_usable()
        if not helper:
            helper = ensure_aur_helper()
        if helper:
            subprocess.run([helper, "-S", "--needed", "--noconfirm", *aur_pkgs], check=False)

    if has_fcitx and shutil.which("fcitx5"):
        try:
            from nyxniri.fcitx import fcitx_install
            fcitx_install()
        except Exception:
            pass

    print(msg("opt_apps_install_done"))


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
        install_optional_apps(chosen)
    else:
        print(msg("opt_apps_none_selected"))
