"""TUI completion screen rendering for deployment results."""
import subprocess
import sys
import time
from typing import List, Optional
from nyxniri.colors import Colors
from nyxniri.constants import REPO_URL
from nyxniri.env import get_env
from nyxniri.i18n import msg
from nyxniri.tui import show_logo, read_key, responsive_hint, render_menu_item
from nyxniri.deploy_core import discover_config_items
from nyxniri.wallpapers import wallpapers_pack_present, WallpaperDeployResult


def render_completion_screen(
    mode: str = "install",
    chosen_items: Optional[List[str]] = None,
    preserved_lines: Optional[List[str]] = None,
    wallpaper_result: Optional[WallpaperDeployResult] = None,
    do_fcitx: bool = False,
    do_greeter: bool = False,
    failed_items: Optional[List[str]] = None,
) -> None:
    if chosen_items is None:
        chosen_items = discover_config_items()
    if preserved_lines is None:
        preserved_lines = []
    if failed_items is None:
        failed_items = []
    from nyxniri.fcitx import fcitx5_installed, fcitx_enabled
    from nyxniri.deps import get_missing_deps
    title_key = "summary_title_failed" if failed_items else ("summary_title_update" if mode == "update" else ("summary_title_test" if mode == "test" else "summary_title_install"))
    missing_deps = get_missing_deps() if mode == "full" else []

    def _render_body():
        title_color = Colors.BOLD_RED if failed_items else Colors.BOLD_GREEN
        sys.stdout.write(f"  {title_color}{msg(title_key)}{Colors.RESET}\n\n")
        sys.stdout.write(f"  {Colors.BOLD_WHITE}{msg('summary_section_details')}{Colors.RESET}\n")
        if failed_items:
            sys.stdout.write(f"    {Colors.BOLD_RED}[✗]{Colors.RESET} {msg('summary_item_configs_failed', ', '.join(failed_items))}\n")
        elif chosen_items or mode == "test":
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_configs_ok', len(chosen_items))}\n")
        else:
            sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_configs_skip')}\n")
        if mode in ("full", "update", "test"):
            if wallpaper_result and wallpaper_result.downloaded:
                wk, wc, wi = "summary_item_wallpapers_downloaded", Colors.BOLD_GREEN, "[✓]"
            elif wallpaper_result and wallpaper_result.download_failed and wallpaper_result.pack_present:
                wk, wc, wi = "summary_item_wallpapers_refresh_failed", Colors.BOLD_YELLOW, "[!]"
            elif wallpaper_result and wallpaper_result.download_failed and wallpaper_result.fallback_synced:
                wk, wc, wi = "summary_item_wallpapers_failed_fallback", Colors.BOLD_YELLOW, "[!]"
            elif wallpaper_result and wallpaper_result.download_failed:
                wk, wc, wi = "summary_item_wallpapers_failed", Colors.BOLD_RED, "[✗]"
            elif (wallpaper_result and wallpaper_result.pack_present) or wallpapers_pack_present():
                wk, wc, wi = "summary_item_wallpapers_existing", Colors.BOLD_GREEN, "[✓]"
            elif wallpaper_result and wallpaper_result.fallback_synced:
                wk, wc, wi = "summary_item_wallpapers_fallback", Colors.BOLD_YELLOW, "[!]"
            else:
                wk, wc, wi = "summary_item_wallpapers_skip", Colors.BOLD_YELLOW, "[!]"
            sys.stdout.write(f"    {wc}{wi}{Colors.RESET} {msg(wk)}\n")
        if mode in ("full", "update", "test") and fcitx5_installed():
            if do_fcitx or fcitx_enabled():
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_fcitx_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_fcitx_skip')}\n")
        if mode == "full":
            if not missing_deps:
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_deps_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_deps_skip')}\n")
        if do_greeter:
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_greeter_ok')}\n")
        if preserved_lines:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}\n")
            for pline in sorted(set(preserved_lines)):
                sys.stdout.write(f"    {pline}\n")
    if not sys.stdin.isatty() or mode == "test":
        sys.stdout.write(Colors.CLEAR_SCREEN)
        show_logo()
        _render_body()
        sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_next')}{Colors.RESET}\n")
        sys.stdout.write(f"    {msg('summary_next_start')}\n")
        sys.stdout.write(f"    {msg('summary_next_manual')}\n")
        sys.stdout.write(f"    {msg('summary_next_panel')}\n\n")
        return
    from nyxniri.deps import run_optional_apps_menu_loop
    import shutil
    focus = 0
    sys.stdout.write(Colors.CURSOR_HIDE)
    try:
        while True:
            sys.stdout.write(Colors.CLEAR_SCREEN)
            show_logo()
            _render_body()
            sys.stdout.write(msg("summary_action_title"))
            render_menu_item(0, msg("summary_action_apps"), focus)
            render_menu_item(1, msg("summary_action_star"), focus)
            render_menu_item(2, msg("summary_action_exit"), focus, style="subtle")
            sys.stdout.write(f"\n{responsive_hint('summary_action_hint')}\n")
            sys.stdout.flush()
            key = read_key()
            if key in ("UP", "k", "K"):
                focus = 2 if focus <= 0 else focus - 1
            elif key in ("DOWN", "j", "J"):
                focus = 0 if focus >= 2 else focus + 1
            elif key in ("ENTER", "SPACE"):
                if focus == 0:
                    run_optional_apps_menu_loop()
                elif focus == 1:
                    star_url = REPO_URL.removesuffix(".git")
                    if shutil.which("xdg-open"):
                        subprocess.run(["xdg-open", star_url], check=False, timeout=5)
                    print(msg("msg_star_opened", star_url))
                    time.sleep(1.2)
                elif focus == 2:
                    break
            elif key in ("0", "q", "Q", "ESC", "EXIT"):
                break
    finally:
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()
