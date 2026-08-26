"""Atomic dotfiles deployment, template rendering, Dunder preservation, and hardware patching."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional
from nyxniri.constants import (
    FCITX_THEME,
    GREETER_PKG,
    MAIN_WM,
    MAIN_WM_HARDWARE_CONFIG,
    PROJECT_NAME,
    REPO_URL,
    THEME_ENGINE,
)
from nyxniri.env import get_env, get_pics_dir
from nyxniri.log import log_msg
from nyxniri.cleanup import register_temp_path
from nyxniri.utils import _remove_path
from nyxniri.i18n import msg
from nyxniri.network import fetch_raw_with_fallback
from nyxniri.colors import Colors

_SCRIPTS_TO_CHMOD = [
    "fish/clean-cache",
    f"{THEME_ENGINE}/theme-sync.sh",
    f"{THEME_ENGINE}/wallpaper-hook.sh",
    f"{THEME_ENGINE}/mpvpaper-sync.sh",
    f"{MAIN_WM}/scripts/toggle-eyecare.sh",
    f"{MAIN_WM}/scripts/niri-scratch-toggle.sh",
    f"{MAIN_WM}/scripts/orbit-launcher.py",
    f"{MAIN_WM}/scripts/niri-scratch-menu.py",
    f"{MAIN_WM}/scripts/wallpaper-picker.py",
]
_CONFIG_ITEMS_CACHE: List[str] = []


def discover_config_items() -> List[str]:
    global _CONFIG_ITEMS_CACHE
    if _CONFIG_ITEMS_CACHE:
        return _CONFIG_ITEMS_CACHE
    env = get_env()
    if env.configs_src.is_dir():
        items = [p.name for p in env.configs_src.iterdir() if p.name != "__pycache__"]
        if items:
            _CONFIG_ITEMS_CACHE = sorted(items)
            return _CONFIG_ITEMS_CACHE
    _CONFIG_ITEMS_CACHE = ["fastfetch", "fish", "kitty", "niri", "noctalia", "starship.toml", "xdg-desktop-portal", "zed"]
    return _CONFIG_ITEMS_CACHE


def atomic_replace_item(src: Path, dest: Path, preserved_log: Optional[List[str]] = None, test_mode: bool = False) -> bool:
    pid = os.getpid()
    dest_parent = dest.parent
    home = get_env().home
    if src.is_file():
        tmp_file = dest.with_name(f"{dest.name}.new.{pid}")
        register_temp_path(tmp_file)
        old_dest = None
        try:
            dest_parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp_file)
            if dest.exists() or dest.is_symlink():
                old_dest = dest.with_name(f"{dest.name}.old.{pid}")
                dest.rename(old_dest)
                tmp_file.rename(dest)
                _remove_path(old_dest)
            else:
                tmp_file.rename(dest)
            return True
        except Exception as e:
            _remove_path(tmp_file)
            if old_dest is not None and old_dest.exists():
                try:
                    old_dest.rename(dest)
                except Exception:
                    pass
            log_msg("ERROR", f"Atomic replace failed for {dest}: {e}")
            return False

    tmp_new = dest.with_name(f"{dest.name}.new.{pid}")
    register_temp_path(tmp_new)
    try:
        dest_parent.mkdir(parents=True, exist_ok=True)
        if tmp_new.exists() or tmp_new.is_symlink():
            _remove_path(tmp_new)
        shutil.copytree(src, tmp_new, symlinks=True)
        if dest.is_dir():
            for root, dirs, files in os.walk(dest):
                dirs[:] = [d for d in dirs if "__custom__" not in d]
                for f in files:
                    if "__custom__" in f:
                        if test_mode and f in ("scratchpad-items__custom__.toml", "orbit-items__custom__.toml"):
                            continue
                        rel_path = Path(root).relative_to(dest) / f
                        src_custom = dest / rel_path
                        target_custom = tmp_new / rel_path
                        target_custom.parent.mkdir(parents=True, exist_ok=True)
                        if src_custom.is_symlink():
                            target_custom.unlink(missing_ok=True)
                            target_custom.symlink_to(os.readlink(src_custom))
                        else:
                            shutil.copy2(src_custom, target_custom)
                        rel_display = str(dest.relative_to(home / ".config") / rel_path)
                        print(msg("log_keep_custom_file", rel_display))
                        if preserved_log is not None:
                            preserved_log.append(f"~/.config/{rel_display}")
            for root, dirs, _ in os.walk(dest):
                for d in list(dirs):
                    if "__custom__" in d:
                        dirs.remove(d)
                        rel_dir = Path(root).relative_to(dest) / d
                        src_custom_dir = dest / rel_dir
                        target_custom_dir = tmp_new / rel_dir
                        target_custom_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.rmtree(target_custom_dir, ignore_errors=True)
                        shutil.copytree(src_custom_dir, target_custom_dir, symlinks=True)
                        rel_display = str(dest.relative_to(home / ".config") / rel_dir)
                        print(msg("log_keep_custom_dir", rel_display))
                        if preserved_log is not None:
                            preserved_log.append(f"~/.config/{rel_display}/")
        if dest.exists() or dest.is_symlink():
            old_dest = dest.with_name(f"{dest.name}.old.{pid}")
            dest.rename(old_dest)
            try:
                tmp_new.rename(dest)
                _remove_path(old_dest)
            except Exception:
                old_dest.rename(dest)
                raise
            return True
        else:
            tmp_new.rename(dest)
            return True
    except Exception as e:
        _remove_path(tmp_new)
        log_msg("ERROR", f"Atomic replace failed for directory {dest}: {e}")
        return False


def _phase_atomic_deployment(items_to_deploy, keep_monitor=True, preserved_log=None, test_mode=False):
    env = get_env()
    home = env.home
    config_dir = env.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    failed_items = []
    for item in items_to_deploy:
        src = env.configs_src / item
        dest = config_dir / item
        if src.exists():
            temp_monitor = None
            if item == MAIN_WM and (dest / MAIN_WM_HARDWARE_CONFIG).is_file():
                if keep_monitor or os.environ.get("NYXNIRI_KEEP_MONITOR", "0") == "1":
                    tfd, tname = tempfile.mkstemp()
                    os.close(tfd)
                    temp_monitor = Path(tname)
                    register_temp_path(temp_monitor)
                    shutil.copy2(dest / MAIN_WM_HARDWARE_CONFIG, temp_monitor)
            if not atomic_replace_item(src, dest, preserved_log=preserved_log, test_mode=test_mode):
                failed_items.append(item)
                print(msg("log_deploy_config_failed", item), file=sys.stderr)
                continue
            if temp_monitor and temp_monitor.is_file():
                shutil.copy2(temp_monitor, dest / MAIN_WM_HARDWARE_CONFIG)
                temp_monitor.unlink(missing_ok=True)
                print(msg("log_keep_monitor_config", MAIN_WM, MAIN_WM_HARDWARE_CONFIG))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{MAIN_WM}/{MAIN_WM_HARDWARE_CONFIG}")
            print(msg("log_deploy_config_item", item))
            log_msg("INFO", f"Deployed config ~/.config/{item}")
        else:
            failed_items.append(item)
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            log_msg("ERROR", f"Missing config source: {src}")
    for rel in _SCRIPTS_TO_CHMOD:
        p = config_dir / rel
        if p.is_file():
            p.chmod(0o755)
    effects_normal = config_dir / MAIN_WM / "effects_normal.kdl"
    effects_sym = config_dir / MAIN_WM / "effects.kdl"
    if effects_normal.is_file() and not effects_sym.exists():
        try:
            effects_sym.symlink_to(effects_normal)
        except Exception:
            pass
    return failed_items


def _phase_render_templates():
    env = get_env()
    home = env.home
    config_dir = env.config_dir
    wp_dest = get_pics_dir() / "Wallpapers"
    noctalia_conf = config_dir / THEME_ENGINE / f"{THEME_ENGINE}-config.toml"
    if noctalia_conf.is_file():
        content = noctalia_conf.read_text(encoding="utf-8", errors="replace")
        content = re.sub(r'^directory = ".*"', f'directory = "{wp_dest}"', content, flags=re.MULTILINE)
        content = re.sub(r'^video_directory = ".*"', f'video_directory = "{wp_dest / "video"}"', content, flags=re.MULTILINE)
        content = content.replace("/home/user", str(home))
        noctalia_conf.write_text(content, encoding="utf-8")
    niri_conf = config_dir / MAIN_WM / "config.kdl"
    if niri_conf.is_file():
        content = niri_conf.read_text(encoding="utf-8", errors="replace")
        content = content.replace("/home/user", str(home))
        pics_dir = get_pics_dir()
        if str(pics_dir).startswith(str(home)):
            rel_pics = "~" + str(pics_dir)[len(str(home)):]
        else:
            rel_pics = str(pics_dir)
        screenshot_target = f'screenshot-path "{rel_pics}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"'
        content = re.sub(r'^\s*(//)?\s*screenshot-path\s+.*', screenshot_target, content, flags=re.MULTILINE)
        niri_conf.write_text(content, encoding="utf-8")
    fish_vars = config_dir / "fish" / "fish_variables"
    if fish_vars.is_file():
        content = fish_vars.read_text(encoding="utf-8", errors="replace")
        content = content.replace("/home/user", str(home))
        fish_vars.write_text(content, encoding="utf-8")

_IS_NVIDIA = None

def _detect_nvidia():
    global _IS_NVIDIA
    if _IS_NVIDIA is not None:
        return _IS_NVIDIA
    try:
        res = subprocess.run(["lspci"], capture_output=True, text=True, check=False, env={**os.environ, "LC_ALL": "C"})
        _IS_NVIDIA = "nvidia" in res.stdout.lower()
    except Exception:
        _IS_NVIDIA = False
    return _IS_NVIDIA


def _phase_hardware_patches():
    env = get_env()
    niri_conf = env.config_dir / MAIN_WM / "config.kdl"
    if not niri_conf.is_file():
        return
    if _detect_nvidia():
        print(msg("log_nvidia_gpu_detected"))
        log_msg("INFO", "NVIDIA GPU detected. Enabling NVIDIA envs in config.kdl")
        content = niri_conf.read_text(encoding="utf-8")
        content = re.sub(r'^(\s*)//\s*(GBM_BACKEND\s+"nvidia-drm")', r'', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)//\s*(__GLX_VENDOR_LIBRARY_NAME\s+"nvidia")', r'', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)//\s*(LIBVA_DRIVER_NAME\s+"nvidia")', r'', content, flags=re.MULTILINE)
        niri_conf.write_text(content, encoding="utf-8")
    else:
        print(msg("log_nvidia_gpu_not_detected"))
        log_msg("INFO", "Non-NVIDIA GPU detected. NVIDIA envs kept disabled.")


def _phase_post_install_services():
    env = get_env()
    config_dir = env.config_dir
    sync_script = config_dir / THEME_ENGINE / "theme-sync.sh"
    if sync_script.is_file():
        sync_script.chmod(0o755)
        subprocess.run(["bash", str(sync_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print(msg("log_gtk_theme_init"))
    if shutil.which(THEME_ENGINE):
        from nyxniri.gtktheme import gtktheme_trigger_render
        gtktheme_trigger_render()
        print(msg("log_enable_mpvpaper"))
        subprocess.run([THEME_ENGINE, "msg", "plugins", "enable", f"{THEME_ENGINE}/mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if shutil.which("fish"):
        print(msg("log_check_fisher"))
        log_msg("INFO", "Checking Fisher plugin manager installation")
        fish_check = subprocess.run(["fish", "-c", "functions -q fisher; echo $status"], capture_output=True, text=True, check=False)
        if fish_check.returncode == 0 and fish_check.stdout.strip() == "0":
            log_msg("INFO", "Fisher already installed, running update")
            subprocess.run(["fish", "-c", "fisher update"], check=False)
        else:
            tfd, tname = tempfile.mkstemp(suffix=".fish")
            os.close(tfd)
            fisher_path = Path(tname)
            register_temp_path(fisher_path)
            msg_install = msg("log_install_fish_plugins")
            msg_skip = msg("log_fisher_update_skipped")
            if fetch_raw_with_fallback("jorgebucaran/fisher", "main", "functions/fisher.fish", fisher_path):
                fish_code = (
                    f"if not functions -q fisher; source '{fisher_path}' && fisher install jorgebucaran/fisher; end; "
                    f"if test -f ~/.config/fish/fish_plugins && functions -q fisher; "
                    f"echo '{msg_install}'; fisher update || echo '{msg_skip}'; end"
                )
                subprocess.run(["fish", "-c", fish_code], check=False)
            else:
                print(msg("log_fisher_install_skipped"))
                log_msg("WARN", "Fisher auto-install skipped (network unreachable)")


def deploy_selected_configs(do_backup=False, items_to_deploy=None, preserved_log=None):
    if items_to_deploy is None:
        items_to_deploy = discover_config_items()
    if preserved_log is None:
        preserved_log = []
    if do_backup:
        from nyxniri.backup import backup_configs
        backup_configs(note="auto_snapshot_before_deploy", interactive=False)
    print(msg("copying_configs"))
    failed_items = _phase_atomic_deployment(items_to_deploy, keep_monitor=True, preserved_log=preserved_log)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        return failed_items
    _phase_render_templates()
    _phase_hardware_patches()
    _phase_post_install_services()
    print(msg("copy_done"))
    return []


def test_deploy():
    print(msg("test_start"))
    os.environ["NYXNIRI_KEEP_MONITOR"] = "1"
    preserved_log = []
    items = discover_config_items()
    failed_items = _phase_atomic_deployment(items, keep_monitor=True, preserved_log=preserved_log, test_mode=True)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        from nyxniri.completion import render_completion_screen
        render_completion_screen(mode="test", chosen_items=items, preserved_lines=preserved_log, failed_items=failed_items)
        return False
    _phase_render_templates()
    _phase_hardware_patches()
    from nyxniri.wallpapers import deploy_wallpapers
    wallpaper_result = deploy_wallpapers(do_download=False)
    from nyxniri.completion import render_completion_screen
    render_completion_screen(mode="test", chosen_items=items, preserved_lines=preserved_log, wallpaper_result=wallpaper_result)
    return True
