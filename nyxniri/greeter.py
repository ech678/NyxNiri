"""Optional Noctalia Greeter (greetd login) installation and system setup."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from nyxniri.constants import (
    Colors,
    GREETER_ETC_CFG,
    GREETER_PKG,
    GREETER_POLKIT_RULE,
    GREETER_SESSION_BIN,
    MAIN_WM,
    THEME_ENGINE,
)
from nyxniri.core import log_msg
from nyxniri.i18n import get_lang, msg


def _text(zh: str, en: str) -> str:
    return zh if get_lang() == "zh" else en

CONFLICT_DMS = ["sddm", "lightdm", "gdm", "ly"]

def greeter_installed() -> bool:
    """Check if noctalia-greeter session binary exists in PATH."""
    return shutil.which(GREETER_SESSION_BIN) is not None

def greeter_status_label() -> str:
    """Return compact status label for menus."""
    if not greeter_installed():
        return msg("status_not_installed")

    cfg_ok = False
    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                cfg_ok = True
        except Exception:
            pass

    enabled = False
    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "is-enabled", "greetd"], capture_output=True, check=False)
        enabled = res.returncode == 0

    if enabled and cfg_ok:
        return msg("status_installed_enabled")
    return msg("status_installed")

def _greeter_session_arg() -> str:
    """Check if niri session is discoverable by noctalia-greeter."""
    if shutil.which(GREETER_PKG):
        try:
            res = subprocess.run([GREETER_PKG, "sessions"], capture_output=True, text=True, check=False)
            if MAIN_WM.lower() in res.stdout.lower():
                return f"-- --session {MAIN_WM}"
        except Exception:
            pass
    return ""

def greeter_install_packages() -> bool:
    """Install greetd and noctalia-greeter."""
    from nyxniri.deps import ensure_aur_helper, get_preferred_pkg_manager
    print(msg("greeter_install_pkgs"))

    pkg_mgr = get_preferred_pkg_manager()
    is_aur = pkg_mgr != ["sudo", "pacman"]

    # Check greetd
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", "greetd"], capture_output=True, check=False)
        if res.returncode != 0:
            subprocess.run([*pkg_mgr, "-S", "--noconfirm", "greetd"], check=False)

    if not greeter_installed():
        has_aur_helper = ensure_aur_helper() is not None if not is_aur else True
        if not has_aur_helper:
            print(msg("greeter_aur_required"))
            return False
        res_inst = subprocess.run([*pkg_mgr, "-S", "--noconfirm", GREETER_PKG], check=False)
        if res_inst.returncode != 0 or not greeter_installed():
            print(msg("greeter_install_failed"))
            return False

    return True

def greeter_install() -> bool:
    """Full Noctalia Greeter installation and configuration pipeline."""
    print(msg("greeter_install_title"))

    if not greeter_install_packages():
        return False

    # Check for conflicting display managers
    for dm in CONFLICT_DMS:
        if shutil.which("systemctl"):
            res = subprocess.run(["systemctl", "is-enabled", dm], capture_output=True, check=False)
            if res.returncode == 0:
                print(msg("greeter_dm_conflict", dm))

    # Backup & Write /etc/greetd/config.toml
    sess_path = shutil.which(GREETER_SESSION_BIN) or f"/usr/bin/{GREETER_SESSION_BIN}"
    sess_arg = _greeter_session_arg()
    command_str = f"{sess_path} {sess_arg}".strip()

    toml_content = (
        "[terminal]\n"
        "vt = 1\n\n"
        "[default_session]\n"
        f'command = "{command_str}"\n'
        'user = "greeter"\n'
    )

    bak = Path(f"{GREETER_ETC_CFG}.nyxniri.bak")
    backup_cmd = f"mkdir -p {GREETER_ETC_CFG.parent} && if [ -f {GREETER_ETC_CFG} ] && [ ! -f {bak} ]; then cp {GREETER_ETC_CFG} {bak}; fi"
    subprocess.run(["sudo", "sh", "-c", backup_cmd], check=False)

    write_cmd = f"cat << 'EOF' > {GREETER_ETC_CFG}\n{toml_content}\nEOF"
    res_w = subprocess.run(["sudo", "sh", "-c", write_cmd], check=False)
    if res_w.returncode == 0 and GREETER_ETC_CFG.is_file():
        print(msg("greeter_config_written", str(GREETER_ETC_CFG)))
    else:
        print(msg("greeter_config_failed", str(GREETER_ETC_CFG)))
        return False

    state_cmd = (
        f"mkdir -p /var/lib/{GREETER_PKG} && "
        f"(chown -R greeter:greeter /var/lib/{GREETER_PKG} 2>/dev/null || true) && "
        f"chmod 755 /var/lib/{GREETER_PKG}"
    )
    res_s = subprocess.run(["sudo", "sh", "-c", state_cmd], check=False)
    if res_s.returncode == 0:
        print(msg("greeter_state_dir_created"))

    # Polkit rule
    polkit_rule = (
        'polkit.addRule(function(action, subject) {\n'
        f'    if (action.id == "org.{THEME_ENGINE}.greeter.apply-appearance" && subject.isInGroup("wheel")) {{\n'
        '        return polkit.Result.YES;\n'
        '    }\n'
        '});\n'
    )
    polkit_cmd = f"mkdir -p {GREETER_POLKIT_RULE.parent} && cat << 'EOF' > {GREETER_POLKIT_RULE}\n{polkit_rule}\nEOF"
    res_p = subprocess.run(["sudo", "sh", "-c", polkit_cmd], check=False)
    if res_p.returncode == 0:
        print(msg("greeter_polkit_written", str(GREETER_POLKIT_RULE)))
    else:
        print(msg("greeter_polkit_failed"))

    # Enable greetd
    res_e = subprocess.run(["sudo", "systemctl", "enable", "greetd"], check=False)
    if res_e.returncode == 0:
        print(msg("greeter_enabled"))
    else:
        print(msg("greeter_enable_failed"))

    print(msg("greeter_reboot_hint"))
    log_msg("INFO", "Configured Noctalia Greeter")
    return True

def greeter_status() -> None:
    """Print detailed status of Noctalia Greeter."""
    print(msg("greeter_status_title"))
    if greeter_installed():
        print(msg("doctor_ok", _text(f"{GREETER_PKG}: 已安装", f"{GREETER_PKG}: installed")))
    else:
        print(msg("doctor_warn", _text(f"{GREETER_PKG}: 未安装", f"{GREETER_PKG}: not installed")))

    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                print(msg("doctor_ok", _text(f"greetd 配置: 已使用 {GREETER_PKG}", f"greetd config: using {GREETER_PKG}")))
            else:
                print(msg("doctor_warn", _text(
                    f"greetd 配置存在，但未使用 {GREETER_PKG}",
                    f"greetd config exists but does not use {GREETER_PKG}",
                )))
        except Exception:
            pass
    else:
        print(msg("doctor_warn", _text(f"greetd 配置缺失: {GREETER_ETC_CFG}", f"greetd config is missing: {GREETER_ETC_CFG}")))

    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "is-enabled", "greetd"], capture_output=True, check=False)
        if res.returncode == 0:
            print(msg("doctor_ok", _text("greetd 服务: 已启用", "greetd service: enabled")))
        else:
            print(msg("doctor_warn", _text("greetd 服务: 未启用", "greetd service: disabled")))

def greeter_uninstall() -> bool:
    """Uninstall Noctalia Greeter configuration and restore backups."""
    print(msg("greeter_uninstall_title"))

    bak = Path(f"{GREETER_ETC_CFG}.nyxniri.bak")
    if bak.is_file():
        restore_cmd = f"cp {bak} {GREETER_ETC_CFG} 2>/dev/null; rm -f {bak}"
        subprocess.run(["sudo", "sh", "-c", restore_cmd], check=False)
        if GREETER_ETC_CFG.is_file():
            print(msg("greeter_uninstall_restored", str(GREETER_ETC_CFG)))
        else:
            print(msg("greeter_uninstall_nobackup"))
    else:
        print(msg("greeter_uninstall_nobackup"))

    if GREETER_POLKIT_RULE.is_file():
        subprocess.run(["sudo", "rm", "-f", str(GREETER_POLKIT_RULE)], check=False)
        print(msg("greeter_uninstall_polkit"))

    print(msg("greeter_uninstall_done"))
    log_msg("INFO", "Uninstalled Noctalia Greeter configuration")
    return True
