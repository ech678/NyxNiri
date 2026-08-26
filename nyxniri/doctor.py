"""System health diagnostics (System Doctor) and diagnostic report exporter."""

import datetime
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from nyxniri.constants import (
    Colors,
    FCITX_THEME,
    MAIN_WM,
    PROJECT_NAME,
    THEME_ENGINE,
)
from nyxniri.env import get_env, get_pics_dir
from nyxniri.log import log_msg
from nyxniri.i18n import get_lang, msg


def _text(zh: str, en: str) -> str:
    """Select concise diagnostic text for the active interface language."""
    return zh if get_lang() == "zh" else en

def _check_compositor(env) -> None:
    xdg_curr = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if xdg_curr.lower() == MAIN_WM.lower():
        print(msg("doctor_ok", _text(f"合成器: {MAIN_WM} 正在运行", f"Compositor: {MAIN_WM} is running")))
    else:
        current = xdg_curr or _text("未知", "Unknown")
        print(msg("doctor_warn", _text(
            f"合成器: 当前桌面为 {current}，{MAIN_WM} 未运行",
            f"Compositor: current desktop is {current}; {MAIN_WM} is not running",
        )))

def _check_wayland_session(env) -> None:
    sess_file = Path(f"/usr/share/wayland-sessions/{MAIN_WM}.desktop")
    if sess_file.is_file():
        print(msg("doctor_ok", _text(f"会话: {MAIN_WM} Wayland 入口已注册", f"Session: {MAIN_WM} Wayland entry is registered")))
    else:
        print(msg("doctor_warn", _text(f"会话: 缺少 {sess_file}", f"Session: {sess_file} is missing")))

def _check_noctalia(env) -> None:
    if not shutil.which(THEME_ENGINE):
        print(msg("doctor_err", _text(f"{THEME_ENGINE}: 未在 PATH 中找到", f"{THEME_ENGINE}: not found in PATH")))
    else:
        try:
            res = subprocess.run([THEME_ENGINE, "msg", "status"], capture_output=True, check=False)
            if res.returncode == 0:
                print(msg("doctor_ok", _text(f"{THEME_ENGINE}: 守护进程响应正常", f"{THEME_ENGINE}: daemon is responding")))
            else:
                print(msg("doctor_err", _text(f"{THEME_ENGINE}: 守护进程未运行", f"{THEME_ENGINE}: daemon is not running")))
        except Exception:
            print(msg("doctor_err", _text(f"{THEME_ENGINE}: 守护进程未运行", f"{THEME_ENGINE}: daemon is not running")))

def _check_wallpapers(env) -> None:
    wp_dir = get_pics_dir() / "Wallpapers"
    if wp_dir.is_dir():
        print(msg("doctor_ok", _text(f"壁纸目录: {wp_dir}", f"Wallpapers: {wp_dir}")))
    else:
        print(msg("doctor_err", _text(f"壁纸目录不存在: {wp_dir}", f"Wallpapers directory is missing: {wp_dir}")))

def _check_core_deps(env) -> None:
    missing = 0
    for cmd in (MAIN_WM, THEME_ENGINE, "fish", "starship"):
        if not shutil.which(cmd):
            print(msg("doctor_err", _text(f"依赖: PATH 中缺少 {cmd}", f"Dependency: {cmd} is missing from PATH")))
            missing += 1
    if missing == 0:
        tools = f"{MAIN_WM}, {THEME_ENGINE}, fish, starship"
        print(msg("doctor_ok", _text(f"核心依赖已安装: {tools}", f"Core dependencies installed: {tools}")))

def _check_scripts(env) -> None:
    config_dir = env.config_dir
    scripts_info = [
        (f"{THEME_ENGINE}/theme-sync.sh", "theme-sync.sh"),
        (f"{THEME_ENGINE}/wallpaper-hook.sh", "wallpaper-hook.sh"),
        (f"{THEME_ENGINE}/mpvpaper-sync.sh", "mpvpaper-sync.sh"),
        ("fish/clean-cache", "clean-cache"),
        (f"{MAIN_WM}/scripts/toggle-eyecare.sh", "toggle-eyecare.sh"),
        (f"{MAIN_WM}/scripts/niri-scratch-toggle.sh", "niri-scratch-toggle.sh"),
        (f"{MAIN_WM}/scripts/orbit-launcher.py", "orbit-launcher.py"),
        (f"{MAIN_WM}/scripts/niri-scratch-menu.py", "niri-scratch-menu.py"),
        (f"{MAIN_WM}/scripts/wallpaper-picker.py", "wallpaper-picker.py"),
    ]
    for rel_path, name in scripts_info:
        full_path = config_dir / rel_path
        if not full_path.is_file() and (config_dir / MAIN_WM / name).is_file():
            full_path = config_dir / MAIN_WM / name
        if full_path.is_file():
            if os.access(full_path, os.X_OK):
                print(msg("doctor_ok", _text(f"脚本可执行: {name}", f"Script is executable: {name}")))
            else:
                print(msg("doctor_warn", _text(f"脚本缺少执行权限，正在修复: {name}", f"Script was not executable; fixing: {name}")))
                full_path.chmod(0o755)
        elif name == "clean-cache":
            print(msg("doctor_err", _text("脚本缺失: ~/.config/fish/clean-cache", "Script missing: ~/.config/fish/clean-cache")))

def _check_eyecare(env) -> None:
    if shutil.which("wlsunset"):
        print(msg("doctor_ok", _text("护眼模式: wlsunset 已安装", "Eye Care: wlsunset is installed")))
    else:
        print(msg("doctor_warn", _text("护眼模式: 缺少 wlsunset", "Eye Care: wlsunset is missing")))

def _check_scratchpad(env) -> None:
    if shutil.which("tmux"):
        print(msg("doctor_ok", _text("Scratchpad: tmux 已安装", "Scratchpad: tmux is installed")))
    else:
        print(msg("doctor_warn", _text("Scratchpad: 缺少 tmux", "Scratchpad: tmux is missing")))

def _check_orbit(env) -> None:
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('GtkLayerShell', '0.1')"],
            capture_output=True, check=False,
        )
        if res.returncode == 0:
            print(msg("doctor_ok", _text("Orbit: GtkLayerShell Python 运行环境可用", "Orbit: GtkLayerShell Python runtime is available")))
        else:
            print(msg("doctor_warn", _text(
                "Orbit: 缺少 GtkLayerShell Python 绑定，请安装 python-gobject 与 gtk-layer-shell",
                "Orbit: GtkLayerShell Python bindings are missing; install python-gobject and gtk-layer-shell",
            )))
    except Exception:
        print(msg("doctor_warn", _text("Orbit: 缺少 GtkLayerShell Python 绑定", "Orbit: GtkLayerShell Python bindings are missing")))

def _check_shell(env) -> None:
    curr_shell = os.environ.get("SHELL", "")
    if "fish" in curr_shell:
        print(msg("doctor_ok", _text(f"默认 Shell: fish ({curr_shell})", f"Default shell: fish ({curr_shell})")))
    else:
        current = curr_shell or _text("未知", "Unknown")
        print(msg("doctor_warn", _text(
            f"默认 Shell: {current}；可运行 chsh -s /usr/bin/fish 切换",
            f"Default shell: {current}; use chsh -s /usr/bin/fish to switch",
        )))

def _check_fisher(env) -> None:
    if (env.config_dir / "fish" / "fish_plugins").is_file():
        print(msg("doctor_ok", _text("Fisher: fish_plugins 已部署", "Fisher: fish_plugins is deployed")))
    else:
        print(msg("doctor_warn", _text("Fisher: 缺少 ~/.config/fish/fish_plugins", "Fisher: ~/.config/fish/fish_plugins is missing")))

def _check_audio(env) -> None:
    if shutil.which("wpctl"):
        print(msg("doctor_ok", _text("音频控制: wpctl (WirePlumber) 可用", "Audio Control: wpctl (WirePlumber) is available")))
    else:
        print(msg("doctor_warn", _text("音频控制: 缺少 wpctl", "Audio Control: wpctl is missing")))

def _check_brightness(env) -> None:
    if shutil.which("ddcutil") or shutil.which("brightnessctl"):
        print(msg("doctor_ok", _text("亮度控制: ddcutil / brightnessctl 可用", "Brightness Control: ddcutil / brightnessctl is available")))
    else:
        print(msg("doctor_warn", _text("亮度控制: 缺少 ddcutil 和 brightnessctl", "Brightness Control: ddcutil and brightnessctl are missing")))

def _check_portal_active(env) -> None:
    portal_active = False
    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "--user", "is-active", "xdg-desktop-portal"], capture_output=True, check=False)
        portal_active = res.returncode == 0
    if not portal_active:
        try:
            res = subprocess.run(["pgrep", "-f", "xdg-desktop-portal"], capture_output=True, check=False)
            portal_active = res.returncode == 0
        except Exception:
            pass
    if portal_active:
        print(msg("doctor_ok", _text("桌面门户: xdg-desktop-portal 正在运行", "Desktop Portal: xdg-desktop-portal is active")))
    else:
        print(msg("doctor_warn", _text("桌面门户: xdg-desktop-portal 未运行", "Desktop Portal: xdg-desktop-portal is not active")))

def _check_portal_gtk(env) -> None:
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", "xdg-desktop-portal-gtk"], capture_output=True, check=False)
        if res.returncode == 0:
            print(msg("doctor_ok", _text("桌面门户: xdg-desktop-portal-gtk 后端已安装", "Desktop Portal: xdg-desktop-portal-gtk backend is installed")))
        else:
            print(msg("doctor_warn", _text("桌面门户: 缺少 xdg-desktop-portal-gtk", "Desktop Portal: xdg-desktop-portal-gtk is missing")))

def _check_portal_config(env) -> None:
    portal_conf = env.config_dir / "xdg-desktop-portal" / "niri-portals.conf"
    portal_conf2 = env.config_dir / "xdg-desktop-portal" / "portals.conf"
    if portal_conf.is_file() or portal_conf2.is_file():
        print(msg("doctor_ok", _text("桌面门户: niri-portals.conf 路由已配置", "Desktop Portal: niri-portals.conf routing is configured")))

_MIN_HOME_FREE_KIB = 10 * 1024 * 1024
_GIB_KIB = 1024 * 1024
_MIB_KIB = 1024

def _check_disk_space(env) -> None:
    try:
        res = subprocess.run(["df", "-k", "--output=avail", str(env.home)], capture_output=True, text=True, check=False)
        lines = res.stdout.strip().splitlines()
        if len(lines) >= 2:
            free_kb = int(lines[1].strip())
            if free_kb < _MIN_HOME_FREE_KIB:
                if free_kb >= _GIB_KIB:
                    free_human = f"{free_kb / _GIB_KIB:.1f} GiB"
                elif free_kb >= _MIB_KIB:
                    free_human = f"{free_kb / _MIB_KIB:.1f} MiB"
                else:
                    free_human = f"{free_kb} KiB"
                print(msg("doctor_warn", _text(f"磁盘空间: $HOME 仅剩 {free_human}", f"Disk Space: only {free_human} free on $HOME")))
            else:
                print(msg("doctor_ok", _text("磁盘空间: $HOME 空间充足", "Disk Space: sufficient free space on $HOME")))
    except Exception:
        pass

def _check_fcitx_skin(env) -> None:
    if shutil.which("fcitx5") or (env.config_dir / "fcitx5" / "conf" / "classicui.conf").is_file():
        from nyxniri.fcitx import fcitx_enabled
        if fcitx_enabled():
            print(msg("doctor_ok", _text("Fcitx5: NyxMellow 皮肤已启用", "Fcitx5: NyxMellow skin is enabled")))
        else:
            print(msg("doctor_warn", _text(f"Fcitx5: {FCITX_THEME} 皮肤未启用", f"Fcitx5: {FCITX_THEME} skin not enabled")))

def _check_gtk_theme(env) -> None:
    from nyxniri.gtktheme import gtktheme_registered, gtktheme_rendered
    if gtktheme_rendered():
        print(msg("doctor_ok", _text("GTK 主题: 已渲染并跟随壁纸", "GTK theme: rendered, following wallpaper")))
    elif gtktheme_registered():
        print(msg("doctor_warn", _text(
            "GTK 主题: 模板已注册但未渲染，运行 nyxniri gtk install",
            "GTK theme: registered but not rendered, run nyxniri gtk install",
        )))
    else:
        print(msg("doctor_warn", _text("GTK 主题: 未注册", "GTK theme: not registered")))

def _check_vm(env) -> None:
    if shutil.which("lspci"):
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, check=False, env={**os.environ, "LC_ALL": "C"})
            if re.search(r"VMware|VirtualBox|QEMU|Virtio", res.stdout, re.IGNORECASE):
                print(msg("doctor_warn", _text("检测到虚拟机。请确保 VM 设置中已启用 3D 图形加速", "Virtual Machine detected. Ensure 3D Graphics Acceleration is enabled in VM settings")))
        except Exception:
            pass

def _check_greeter(env) -> None:
    from nyxniri.greeter import greeter_status
    greeter_status()


DOCTOR_CHECKS = [
    _check_compositor,
    _check_wayland_session,
    _check_noctalia,
    _check_wallpapers,
    _check_core_deps,
    _check_scripts,
    _check_eyecare,
    _check_scratchpad,
    _check_orbit,
    _check_shell,
    _check_fisher,
    _check_audio,
    _check_brightness,
    _check_portal_active,
    _check_portal_gtk,
    _check_portal_config,
    _check_disk_space,
    _check_fcitx_skin,
    _check_gtk_theme,
    _check_vm,
    _check_greeter,
]

def run_doctor() -> bool:
    """Execute comprehensive system health diagnosis."""
    print(msg("running_doctor"))
    env = get_env()
    for check in DOCTOR_CHECKS:
        check(env)
    print(msg("all_done"))
    print(msg("reboot_hint"))
    log_msg("INFO", "System Doctor executed")
    return True

def generate_bug_report() -> Optional[Path]:
    """Generate a clean, standardized Markdown bug report aggregating system state."""
    print(msg("generating_report"))
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = env.state_dir / f"nyxniri-bug-report-{timestamp}.md"

    os_name = "Linux"
    if Path("/etc/os-release").is_file():
        for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"\'')
                break

    compositor = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
    session_type = os.environ.get("XDG_SESSION_TYPE", "Unknown")
    shell = os.environ.get("SHELL", "Unknown")

    gpu_info = "Unknown"
    try:
        res = subprocess.run(["lspci"], capture_output=True, text=True, check=False, env={**os.environ, "LC_ALL": "C"})
        gpu_lines = [line for line in res.stdout.splitlines() if "VGA" in line or "3D" in line or "Display" in line]
        if gpu_lines:
            gpu_info = "\n".join(gpu_lines)
    except Exception:
        pass

    displays = "Unknown"
    if shutil.which(MAIN_WM):
        res = subprocess.run([MAIN_WM, "msg", "outputs"], capture_output=True, text=True, check=False)
        displays = res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else f"{MAIN_WM} msg outputs failed"

    tool_lines = []
    for cmd in (MAIN_WM, THEME_ENGINE, "fish", "starship", "kitty", "mpvpaper", "wpctl", "ddcutil", "brightnessctl"):
        if shutil.which(cmd):
            ver = ""
            if cmd == "wpctl":
                res = subprocess.run(["wireplumber", "--version"], capture_output=True, text=True, check=False)
                ver = next((l for l in res.stdout.splitlines() if "libwireplumber" in l.lower()), "")
                if not ver:
                    res = subprocess.run(["pacman", "-Q", "wireplumber"], capture_output=True, text=True, check=False)
                    ver = res.stdout.strip() or "installed"
            elif cmd == "mpvpaper":
                res = subprocess.run(["pacman", "-Q", "mpvpaper", "mpvpaper-git"], capture_output=True, text=True, check=False)
                ver = res.stdout.splitlines()[0] if res.stdout.strip() else "installed"
            else:
                res = subprocess.run([cmd, "--version"], capture_output=True, text=True, check=False)
                ver = res.stdout.splitlines()[0] if res.stdout.strip() else (res.stderr.splitlines()[0] if res.stderr.strip() else "installed")
            tool_lines.append(f"{cmd}: {ver}")
        else:
            tool_lines.append(f"{cmd}: NOT INSTALLED")
    tool_versions = "\n".join(tool_lines)

    daemon_lines = []
    if shutil.which(THEME_ENGINE):
        res = subprocess.run([THEME_ENGINE, "msg", "status"], capture_output=True, text=True, check=False)
        daemon_lines.append(f"--- {THEME_ENGINE} status ---")
        daemon_lines.append(res.stdout.strip() if res.returncode == 0 else f"{THEME_ENGINE} daemon not responding")
    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "--user", "status", "xdg-desktop-portal"], capture_output=True, text=True, check=False)
        daemon_lines.append("\n--- Desktop portal status ---")
        daemon_lines.append("\n".join(res.stdout.splitlines()[:10]) if res.stdout.strip() else "xdg-desktop-portal service check failed")
    daemon_status = "\n".join(daemon_lines)

    health_lines = []
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", "xdg-desktop-portal-gtk"], capture_output=True, text=True, check=False)
        health_lines.append(f"xdg-desktop-portal-gtk: {'installed' if res.returncode == 0 else 'NOT INSTALLED'}")
    try:
        res = subprocess.run(["df", "-h", str(env.home)], capture_output=True, text=True, check=False)
        lines = res.stdout.strip().splitlines()
        if len(lines) >= 2:
            health_lines.append(f"home free space: {lines[1].split()[3]}")
    except Exception:
        pass
    if shutil.which("fcitx5") or (env.config_dir / "fcitx5" / "conf" / "classicui.conf").is_file():
        from nyxniri.fcitx import fcitx_enabled
        health_lines.append(f"fcitx5 nyxmellow: {'enabled' if fcitx_enabled() else 'NOT enabled'}")
    health_checks = "\n".join(health_lines)

    hook_log_path = Path(os.environ.get("XDG_STATE_HOME", str(env.home / ".local" / "state"))) / THEME_ENGINE / "hook.log"
    if hook_log_path.is_file():
        try:
            hook_log = "\n".join(hook_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-20:])
        except Exception:
            hook_log = f"Failed to read {hook_log_path}"
    else:
        hook_log = f"No hook.log found at {hook_log_path}"

    if shutil.which("journalctl"):
        res = subprocess.run(["journalctl", "--user", "-n", "30", "--no-pager"], capture_output=True, text=True, check=False)
        journal = res.stdout.strip() if res.stdout.strip() else "journalctl log access unavailable"
    else:
        journal = "journalctl not available"

    recent_log = "No log found."
    log_path = env.state_dir / "install.log"
    if log_path.is_file():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            recent_log = "\n".join(lines[-30:])
        except Exception:
            pass

    report = (
        f"# NyxNiri Diagnostic Bug Report\n\n"
        f"- **Generated At**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- **NyxNiri Version**: {env.version}\n"
        f"- **Running Mode**: {env.mode_label} ({env.repo_dir})\n\n"
        f"## 1. System Information\n\n"
        f"- **OS**: {os_name}\n"
        f"- **Kernel**: {platform.release()}\n"
        f"- **Architecture**: {platform.machine()}\n"
        f"- **Desktop**: {compositor} ({session_type})\n"
        f"- **Shell**: {shell}\n\n"
        f"## 2. Hardware & GPU\n\n"
        f"```text\n{gpu_info}\n```\n\n"
        f"## 3. Connected Displays\n\n"
        f"```text\n{displays}\n```\n\n"
        f"## 4. Installed Tool Versions\n\n"
        f"```text\n{tool_versions}\n```\n\n"
        f"## 5. Daemon & Service Status\n\n"
        f"```text\n{daemon_status}\n```\n\n"
        f"## 6. NyxNiri Health Checks\n\n"
        f"```text\n{health_checks}\n```\n\n"
        f"## 7. Noctalia Hook Log (Last 20 Lines)\n\n"
        f"```text\n{hook_log}\n```\n\n"
        f"## 8. Systemd User Journal (Last 30 Lines)\n\n"
        f"```text\n{journal}\n```\n\n"
        f"## 9. NyxNiri Installer Log (Last 30 Lines)\n\n"
        f"```text\n{recent_log}\n```\n"
    )

    report_file.write_text(report, encoding="utf-8")
    print(msg("report_done", str(report_file)))
    log_msg("INFO", f"Exported diagnostic bug report to {report_file}")
    return report_file
