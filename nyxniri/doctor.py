"""System health diagnostics (System Doctor) and diagnostic report exporter."""

import datetime
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from nyxniri.constants import (
    Colors,
    MAIN_WM,
    PROJECT_NAME,
    THEME_ENGINE,
)
from nyxniri.core import get_env, get_pics_dir, log_msg
from nyxniri.i18n import get_lang, msg


def _text(zh: str, en: str) -> str:
    """Select concise diagnostic text for the active interface language."""
    return zh if get_lang() == "zh" else en

def run_doctor() -> bool:
    """Execute 11-point comprehensive system health diagnosis."""
    print(msg("running_doctor"))
    all_ok = True
    env = get_env()
    home = env.home
    config_dir = env.config_dir

    # 1. Compositor running check
    xdg_curr = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if xdg_curr.lower() == MAIN_WM.lower():
        print(msg("doctor_ok", _text(f"合成器: {MAIN_WM} 正在运行", f"Compositor: {MAIN_WM} is running")))
    else:
        current = xdg_curr or _text("未知", "Unknown")
        print(msg("doctor_warn", _text(
            f"合成器: 当前桌面为 {current}，{MAIN_WM} 未运行",
            f"Compositor: current desktop is {current}; {MAIN_WM} is not running",
        )))

    # 2. Wayland session desktop file
    sess_file = Path(f"/usr/share/wayland-sessions/{MAIN_WM}.desktop")
    if sess_file.is_file():
        print(msg("doctor_ok", _text(f"会话: {MAIN_WM} Wayland 入口已注册", f"Session: {MAIN_WM} Wayland entry is registered")))
    else:
        print(msg("doctor_warn", _text(f"会话: 缺少 {sess_file}", f"Session: {sess_file} is missing")))

    # 3. Noctalia Daemon status
    if not shutil.which(THEME_ENGINE):
        print(msg("doctor_err", _text(f"{THEME_ENGINE}: 未在 PATH 中找到", f"{THEME_ENGINE}: not found in PATH")))
        all_ok = False
    else:
        try:
            res = subprocess.run([THEME_ENGINE, "msg", "status"], capture_output=True, check=False)
            if res.returncode == 0:
                print(msg("doctor_ok", _text(f"{THEME_ENGINE}: 守护进程响应正常", f"{THEME_ENGINE}: daemon is responding")))
            else:
                print(msg("doctor_err", _text(f"{THEME_ENGINE}: 守护进程未运行", f"{THEME_ENGINE}: daemon is not running")))
        except Exception:
            print(msg("doctor_err", _text(f"{THEME_ENGINE}: 守护进程未运行", f"{THEME_ENGINE}: daemon is not running")))

    # 4. Wallpapers directory
    wp_dir = get_pics_dir() / "Wallpapers"
    if wp_dir.is_dir():
        print(msg("doctor_ok", _text(f"壁纸目录: {wp_dir}", f"Wallpapers: {wp_dir}")))
    else:
        print(msg("doctor_err", _text(f"壁纸目录不存在: {wp_dir}", f"Wallpapers directory is missing: {wp_dir}")))

    # 5. Core dependencies check
    missing_critical = 0
    for cmd in (MAIN_WM, THEME_ENGINE, "fish", "starship"):
        if not shutil.which(cmd):
            print(msg("doctor_err", _text(f"依赖: PATH 中缺少 {cmd}", f"Dependency: {cmd} is missing from PATH")))
            missing_critical += 1
            all_ok = False
    if missing_critical == 0:
        tools = f"{MAIN_WM}, {THEME_ENGINE}, fish, starship"
        print(msg("doctor_ok", _text(f"核心依赖已安装: {tools}", f"Core dependencies installed: {tools}")))

    # 6. Helper script executable permissions
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

    # 7. EyeCare component (wlsunset)
    if shutil.which("wlsunset"):
        print(msg("doctor_ok", _text("护眼模式: wlsunset 已安装", "Eye Care: wlsunset is installed")))
    else:
        print(msg("doctor_warn", _text("护眼模式: 缺少 wlsunset", "Eye Care: wlsunset is missing")))

    # 8. Scratchpad component (tmux)
    if shutil.which("tmux"):
        print(msg("doctor_ok", _text("Scratchpad: tmux 已安装", "Scratchpad: tmux is installed")))
    else:
        print(msg("doctor_warn", _text("Scratchpad: 缺少 tmux", "Scratchpad: tmux is missing")))

    # 9. Orbit launcher runtime (GtkLayerShell)
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('GtkLayerShell', '0.1')"],
            capture_output=True,
            check=False,
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

    # 10. Default Shell
    curr_shell = os.environ.get("SHELL", "")
    if "fish" in curr_shell:
        print(msg("doctor_ok", _text(f"默认 Shell: fish ({curr_shell})", f"Default shell: fish ({curr_shell})")))
    else:
        current = curr_shell or _text("未知", "Unknown")
        print(msg("doctor_warn", _text(
            f"默认 Shell: {current}；可运行 chsh -s /usr/bin/fish 切换",
            f"Default shell: {current}; use chsh -s /usr/bin/fish to switch",
        )))

    # 11. Fisher Plugins
    if (config_dir / "fish" / "fish_plugins").is_file():
        print(msg("doctor_ok", _text("Fisher: fish_plugins 已部署", "Fisher: fish_plugins is deployed")))
    else:
        print(msg("doctor_warn", _text("Fisher: 缺少 ~/.config/fish/fish_plugins", "Fisher: ~/.config/fish/fish_plugins is missing")))

    audio_ok = False
    if shutil.which("pactl") or shutil.which("pwpctl"):
        audio_ok = True
    elif shutil.which("systemctl"):
        for svc in ("pipewire", "pulseaudio"):
            res = subprocess.run(["systemctl", "--user", "is-active", svc], capture_output=True, check=False)
            if res.returncode == 0:
                audio_ok = True
                break
    if audio_ok:
        print(msg("doctor_ok", _text("音频服务: 运行中", "Audio Service: running")))
    else:
        print(msg("doctor_warn", _text("音频服务: 未检测到 PipeWire 或 PulseAudio", "Audio Service: no PipeWire or PulseAudio detected")))

    brightness_ok = False
    if shutil.which("brightnessctl") or shutil.which("light"):
        brightness_ok = True
    elif shutil.which("ddcutil"):
        brightness_ok = True
    if brightness_ok:
        print(msg("doctor_ok", _text("亮度控制: 工具可用", "Brightness Control: tool available")))
    else:
        print(msg("doctor_warn", _text("亮度控制: 未找到 brightnessctl/light/ddcutil", "Brightness Control: brightnessctl/light/ddcutil not found")))

    portal_ok = False
    if shutil.which("xdg-desktop-portal"):
        portal_ok = True
        if shutil.which("systemctl"):
            res = subprocess.run(["systemctl", "--user", "is-active", "xdg-desktop-portal"], capture_output=True, check=False)
            if res.returncode != 0:
                print(msg("doctor_warn", _text("XDG 门户: 已安装但服务未运行", "XDG Portal: installed but service not running")))
            else:
                print(msg("doctor_ok", _text("XDG 门户: 服务运行中", "XDG Portal: service running")))
    else:
        print(msg("doctor_warn", _text("XDG 门户: xdg-desktop-portal 未安装", "XDG Portal: xdg-desktop-portal not installed")))

    try:
        stat = os.statvfs(str(home))
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        if free_gb < 1.0:
            print(msg("doctor_err", _text(f"磁盘空间: 仅剩 {free_gb:.1f} GB", f"Disk Space: only {free_gb:.1f} GB free")))
            all_ok = False
        else:
            print(msg("doctor_ok", _text(f"磁盘空间: 可用 {free_gb:.1f} GB", f"Disk Space: {free_gb:.1f} GB free")))
    except Exception:
        pass

    print(msg("all_done"))
    print(msg("reboot_hint"))
    log_msg("INFO", f"System Doctor executed: {'All checks passed' if all_ok else 'Warnings detected'}")
    return all_ok

def generate_bug_report() -> Optional[Path]:
    """Generate a clean, standardized Markdown bug report aggregating system state."""
    print(msg("generating_report"))
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = env.state_dir / f"nyxniri-bug-report-{timestamp}.md"

    # OS Info
    os_name = "Linux"
    if Path("/etc/os-release").is_file():
        for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"\'')
                break

    # Compositor & Shell
    compositor = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
    session_type = os.environ.get("XDG_SESSION_TYPE", "Unknown")
    shell = os.environ.get("SHELL", "Unknown")

    # GPU
    gpu_info = "Unknown"
    try:
        res = subprocess.run(["lspci"], capture_output=True, text=True, check=False, env={**os.environ, "LC_ALL": "C"})
        gpus = [line for line in res.stdout.splitlines() if "VGA" in line or "3D" in line or "Display" in line]
        if gpus:
            gpu_info = "\n".join(gpus)
    except Exception:
        pass

    display_info = "Unknown"
    try:
        if shutil.which("niri"):
            res = subprocess.run(["niri", "msg", "-j", "outputs"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                import json
                outputs = json.loads(res.stdout)
                display_lines = []
                for out in outputs:
                    name = out.get("name", "?")
                    w = out.get("logical", {}).get("width", "?")
                    h = out.get("logical", {}).get("height", "?")
                    scale = out.get("logical", {}).get("scale", "?")
                    display_lines.append(f"  {name}: {w}x{h} @ {scale}x")
                display_info = "\n".join(display_lines) if display_lines else "No outputs"
    except Exception:
        pass

    tool_versions = []
    for tool in (MAIN_WM, THEME_ENGINE, "fish", "starship", "kitty", "fastfetch", "mpvpaper", "ffmpeg"):
        if shutil.which(tool):
            try:
                res = subprocess.run([tool, "--version"], capture_output=True, text=True, check=False, timeout=5)
                ver_line = (res.stdout or res.stderr).splitlines()[0] if (res.stdout or res.stderr) else "unknown"
                tool_versions.append(f"  {tool}: {ver_line}")
            except Exception:
                tool_versions.append(f"  {tool}: (version check failed)")
    tool_info = "\n".join(tool_versions) if tool_versions else "None found"

    daemon_lines = []
    if shutil.which("systemctl"):
        for svc in (THEME_ENGINE, "greetd", "pipewire", "xdg-desktop-portal"):
            res = subprocess.run(["systemctl", "--user", "is-active", svc], capture_output=True, text=True, check=False)
            state = res.stdout.strip() if res.stdout.strip() else "unknown"
            daemon_lines.append(f"  {svc}: {state}")
    daemon_status = "\n".join(daemon_lines) if daemon_lines else "systemctl not available"

    journal_lines = "No journal available."
    try:
        res = subprocess.run(["journalctl", "--user", "-n", "15", "--no-pager", "-q"], capture_output=True, text=True, check=False, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            journal_lines = res.stdout.strip()
    except Exception:
        pass

    # Recent install log (last 30 lines)
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
        f"## System Information\n\n"
        f"- **OS**: {os_name}\n"
        f"- **Kernel**: {platform.release()}\n"
        f"- **Architecture**: {platform.machine()}\n"
        f"- **Desktop**: {compositor} ({session_type})\n"
        f"- **Shell**: {shell}\n\n"
        f"## Hardware & GPU\n\n"
        f"```text\n{gpu_info}\n```\n\n"
        f"## Display Outputs\n\n"
        f"```text\n{display_info}\n```\n\n"
        f"## Tool Versions\n\n"
        f"```text\n{tool_info}\n```\n\n"
        f"## Daemon Status\n\n"
        f"```text\n{daemon_status}\n```\n\n"
        f"## System Journal (Last 15 lines)\n\n"
        f"```text\n{journal_lines}\n```\n\n"
        f"## Recent Install Log (Last 30 lines)\n\n"
        f"```text\n{recent_log}\n```\n"
    )

    report_file.write_text(report, encoding="utf-8")
    print(msg("report_done", str(report_file)))
    log_msg("INFO", f"Exported diagnostic bug report to {report_file}")
    return report_file
