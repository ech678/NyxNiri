"""CLI entry point, command-line arguments dispatcher, and interactive control panel menus."""

import os
import subprocess
import sys
from typing import List, Optional

from nyxniri.constants import (
    CLI_CMD,
    FCITX_THEME,
    GREETER_PKG,
    PROJECT_NAME,
    THEME_ENGINE,
)
from nyxniri.core import (
    acquire_lock,
    ensure_nyxniri_symlink,
    get_env,
    init_logger,
    log_msg,
)
from nyxniri.deploy import (
    apply_preset,
    deploy_selected_configs,
    deploy_wallpapers,
    discover_config_items,
    get_active_preset,
    list_presets,
    render_completion_screen,
    set_preset,
    test_deploy,
    wallpapers_pack_present,
)
from nyxniri.deps import (
    get_missing_deps,
    install_selected_deps,
    run_dep_menu_loop,
    run_optional_apps_menu_loop,
)
from nyxniri.doctor import generate_bug_report, run_doctor
from nyxniri.fcitx import (
    fcitx_enabled,
    fcitx_install,
    fcitx_status,
    fcitx_status_label,
    fcitx_uninstall,
    fcitx5_installed,
)
from nyxniri.greeter import (
    greeter_install,
    greeter_status,
    greeter_status_label,
    greeter_uninstall,
)
from nyxniri.backup import (
    backup_configs,
    delete_backup,
    list_backups,
    rollback_configs,
    uninstall_nyxniri,
)
from nyxniri.i18n import msg
from nyxniri.network import safe_git_pull
from nyxniri.tui import (
    CheckboxEntry,
    CheckboxList,
    MenuItem,
    Menu,
    pad_display,
    press_any_key,
    prompt_confirm,
    select_language,
)

# --- Master Component Menu & Preflight ---
def run_master_component_menu(is_update: bool = False, mode: str = "full") -> Optional[dict]:
    """Interactive checklist for choosing configs, wallpapers, modules, and backup behavior."""
    items = discover_config_items()
    entries: List[CheckboxEntry] = []

    # 1. Configs
    for item in items:
        entries.append(CheckboxEntry(key=f"config_{item}", label=msg("master_item_config", item), checked=True))

    if mode == "full" or is_update:
        # 2. Heavy assets (wallpapers)
        wp_checked = not wallpapers_pack_present()
        wp_status = msg("status_wallpapers_installed") if wallpapers_pack_present() else msg("status_wallpapers_missing")
        entries.append(CheckboxEntry(
            key="assets_wallpapers",
            label=msg("master_item_asset", f"Wallpapers & Videos {wp_status}"),
            checked=wp_checked,
        ))

        # 3. Fcitx5
        if fcitx5_installed():
            fcitx_check = not (is_update and not fcitx_enabled())
            entries.append(CheckboxEntry(
                key="module_fcitx",
                label=msg("master_item_module", f"NyxMellow fcitx5 {fcitx_status_label()}"),
                checked=fcitx_check,
            ))

        # 4. Greeter
        entries.append(CheckboxEntry(
            key="module_greeter",
            label=msg("master_item_module", f"Noctalia Greeter {greeter_status_label()}"),
            checked=False,
        ))

    # 5. Behavior: Backup
    entries.append(CheckboxEntry(key="sep_behavior", label=msg("master_item_behavior"), is_separator=True))
    entries.append(CheckboxEntry(key="behavior_backup", label=msg("master_item_backup"), checked=True))

    chk = CheckboxList("master_menu_title", entries, hint_key="selective_hint")
    chosen_keys = chk.run()
    if chosen_keys is None:
        return None

    chosen_configs = [k.removeprefix("config_") for k in chosen_keys if k.startswith("config_")]
    do_wallpapers = "assets_wallpapers" in chosen_keys
    do_fcitx = "module_fcitx" in chosen_keys
    do_greeter = "module_greeter" in chosen_keys
    do_backup = "behavior_backup" in chosen_keys

    return {
        "configs": chosen_configs,
        "wallpapers": do_wallpapers,
        "fcitx": do_fcitx,
        "greeter": do_greeter,
        "backup": do_backup,
    }

def _phase_preflight_check(
    mode: str,
    chosen_configs: List[str],
    do_fcitx: bool,
    do_greeter: bool,
    do_wallpapers: bool,
    do_backup: bool,
) -> None:
    """Pre-flight checklist & upfront sudo credentials validation."""
    needs_sudo = mode == "full" or do_greeter

    print(msg("preflight_express_summary"))
    print(msg("preflight_comp_config", len(chosen_configs)))
    if do_wallpapers:
        print(msg("preflight_comp_assets"))
    if do_fcitx:
        print(msg("preflight_comp_module_fcitx", FCITX_THEME))
    if do_greeter:
        print(msg("preflight_comp_module_greeter", GREETER_PKG))
    if mode == "full":
        print(msg("preflight_comp_deps"))
    if do_backup:
        print(msg("preflight_comp_backup"))

    if needs_sudo:
        sys.stdout.write(msg("preflight_sudo_prompt") + "\n")
        sys.stdout.flush()
        sudo_command = ["sudo", "-v"] if sys.stdin.isatty() else ["sudo", "-n", "-v"]
        try:
            res = subprocess.run(sudo_command, check=False)
        except FileNotFoundError:
            print(msg("err_sudo_missing"), file=sys.stderr)
            sys.exit(1)
        if res.returncode != 0:
            print(msg("err_sudo_aborted"))
            sys.exit(1)
        log_msg("INFO", "Sudo credentials cached upfront during pre-flight.")

def install_configs_workflow(mode: str = "full") -> bool:
    """Full execution pipeline for dotfiles, dependencies, wallpapers, and optional modules."""
    if sys.stdin.isatty():
        chosen_dict = run_master_component_menu(is_update=False, mode=mode)
        if not chosen_dict:
            print(msg("install_cancelled"))
            return True

        chosen_configs = chosen_dict["configs"]
        do_wallpapers = chosen_dict["wallpapers"]
        do_fcitx = chosen_dict["fcitx"]
        do_greeter = chosen_dict["greeter"]
        do_backup = chosen_dict["backup"]

        if not chosen_configs and not do_wallpapers and not do_fcitx and not do_greeter:
            print(msg("install_cancelled"))
            return True
    else:
        chosen_configs = discover_config_items()
        do_wallpapers = not wallpapers_pack_present()
        do_fcitx = fcitx_enabled()
        do_greeter = False
        do_backup = False

    _phase_preflight_check(mode, chosen_configs, do_fcitx, do_greeter, do_wallpapers, do_backup)

    # Step counting
    steps = 2  # configs + wallpapers
    if mode == "full":
        steps += 1  # deps
    if do_fcitx:
        steps += 1
    if do_greeter:
        steps += 1
    cur_step = 0

    # 1. Deps
    if mode == "full":
        cur_step += 1
        print(msg("install_step_deps", f"{cur_step}/{steps}"))
        missing = get_missing_deps()
        if missing:
            install_selected_deps(missing)

    # 2. Configs
    cur_step += 1
    print(msg("install_step_configs", f"{cur_step}/{steps}"))
    preserved_log: List[str] = []
    if chosen_configs:
        failed_items = deploy_selected_configs(do_backup=do_backup, items_to_deploy=chosen_configs, preserved_log=preserved_log)
        if failed_items:
            render_completion_screen(
                mode=mode,
                chosen_items=chosen_configs,
                preserved_lines=preserved_log,
                failed_items=failed_items,
            )
            return False

    # 3. Wallpapers (always run — at least syncs offline fallback wallpapers)
    wallpaper_result = None
    cur_step += 1
    print(msg("install_step_wallpapers", f"{cur_step}/{steps}"))
    wallpaper_result = deploy_wallpapers(do_download=do_wallpapers)

    # 4. Fcitx5
    if do_fcitx:
        cur_step += 1
        print(msg("install_step_fcitx", f"{cur_step}/{steps}"))
        fcitx_install()

    # 5. Greeter
    if do_greeter:
        cur_step += 1
        print(msg("install_step_greeter", f"{cur_step}/{steps}"))
        greeter_install()

    # Completion
    render_completion_screen(
        mode=mode,
        chosen_items=chosen_configs,
        preserved_lines=preserved_log,
        wallpaper_result=wallpaper_result,
        do_fcitx=do_fcitx,
        do_greeter=do_greeter,
    )
    return True

def offer_overwrite_upgrade(flag: str = "") -> bool:
    """Handle update flow: ask to deploy changes, view diff, or code update only."""
    env = get_env()
    if flag in ("--force", "--deploy"):
        failed_items = deploy_selected_configs(do_backup=True)
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_result = deploy_wallpapers(do_download=True)
        if fcitx_enabled():
            fcitx_install()
        try:
            greeter_install()
        except Exception as e:
            log_msg("WARN", f"Greeter install skipped during --force update: {e}")
        render_completion_screen("update", wallpaper_result=wallpaper_result)
        return True
    elif flag == "--no-deploy":
        return True

    if not sys.stdin.isatty():
        failed_items = deploy_selected_configs(do_backup=False)
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_result = deploy_wallpapers(do_download=False)
        if fcitx_enabled(): fcitx_install()
        render_completion_screen("update", wallpaper_result=wallpaper_result)
        return True

    # Interactive choice menu
    items = [
        MenuItem(label=msg("overwrite_opt1")),
        MenuItem(label=msg("overwrite_opt2")),
        MenuItem(label=msg("overwrite_opt3"), style="subtle"),
    ]
    menu = Menu("overwrite_title", items, hint_key="submenu_hint")
    choice = menu.run()

    if choice == 0:
        chosen = run_master_component_menu(is_update=True, mode="full")
        if chosen:
            if not chosen["configs"] and not chosen["wallpapers"] and not chosen["fcitx"] and not chosen["greeter"]:
                print(msg("log_no_components_selected"))
                return True
            print(msg("upgrading_selected"))
            preserved: List[str] = []
            if chosen["configs"]:
                failed_items = deploy_selected_configs(do_backup=chosen["backup"], items_to_deploy=chosen["configs"], preserved_log=preserved)
                if failed_items:
                    render_completion_screen("update", chosen_items=chosen["configs"], preserved_lines=preserved, failed_items=failed_items)
                    return False
            wallpaper_result = None
            if chosen["wallpapers"]:
                wallpaper_result = deploy_wallpapers(do_download=True)
            if chosen["fcitx"]:
                fcitx_install()
            if chosen["greeter"]:
                greeter_install()
            render_completion_screen(
                "update",
                chosen_items=chosen["configs"],
                preserved_lines=preserved,
                wallpaper_result=wallpaper_result,
            )
            return True
    elif choice == 1:
        print(msg("diff_viewer_title"))
        config_items = discover_config_items()
        diff_cmds = []
        for it in config_items:
            src = env.configs_src / it
            dest = env.config_dir / it
            if src.exists() and dest.exists():
                diff_cmds.append(f"diff -urN --color=always '{dest}' '{src}'")
        if diff_cmds:
            full_cmd = " ; ".join(diff_cmds) + " | less -R"
            subprocess.run(full_cmd, shell=True, check=False)
    else:
        print(msg("log_config_deploy_skipped"))
    return True

# --- Submenus ---
def check_new_deps_post_update() -> None:
    """Check for newly introduced core dependencies after a repository update."""
    missing = get_missing_deps()
    if not missing:
        return
    print(msg("new_deps_detected", " ".join(missing)))
    if not sys.stdin.isatty():
        log_msg("INFO", f"Auto-installing new deps non-interactively: {' '.join(missing)}")
        install_selected_deps(missing)
        return
    if prompt_confirm("prompt_install_missing_deps", "y"):
        install_selected_deps(missing)
    else:
        print(msg("deps_install_skipped"))


def snapshot_menu_loop() -> None:
    """Snapshot management interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("snapshot_sub_create")),
            MenuItem(label=msg("snapshot_sub_list")),
            MenuItem(label=msg("snapshot_sub_delete"), style="warn"),
            MenuItem(label=msg("snapshot_sub_rollback")),
            MenuItem(label=msg("snapshot_sub_back"), style="subtle"),
        ]
        menu = Menu("snapshot_menu_title", items, hint_key="submenu_hint")
        choice = menu.run()
        if choice == 0:
            sys.stdout.write(msg("snapshot_note_prompt"))
            sys.stdout.flush()
            note = sys.stdin.readline().strip()
            backup_configs(note=note, interactive=True)
            press_any_key()
        elif choice == 1:
            list_backups()
            press_any_key()
        elif choice == 2:
            delete_backup("")
            press_any_key()
        elif choice == 3:
            rollback_configs("")
            press_any_key()
        elif choice == 4:
            break

def greeter_menu_loop() -> None:
    """Noctalia Greeter interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("greeter_sub_install")),
            MenuItem(label=msg("greeter_sub_status")),
            MenuItem(label=msg("greeter_sub_uninstall"), style="warn"),
            MenuItem(label=msg("greeter_sub_back"), style="subtle"),
        ]
        menu = Menu("greeter_menu_title", items, hint_key="submenu_hint")
        choice = menu.run()
        if choice == 0: greeter_install(); press_any_key()
        elif choice == 1: greeter_status(); press_any_key()
        elif choice == 2: greeter_uninstall(); press_any_key()
        elif choice == 3: break

def fcitx_menu_loop() -> None:
    """NyxMellow Fcitx5 skin interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("fcitx_sub_install")),
            MenuItem(label=msg("fcitx_sub_status")),
            MenuItem(label=msg("fcitx_sub_uninstall"), style="warn"),
            MenuItem(label=msg("fcitx_sub_back"), style="subtle"),
        ]
        menu = Menu("fcitx_menu_title", items, hint_key="submenu_hint")
        choice = menu.run()
        if choice == 0: fcitx_install(); press_any_key()
        elif choice == 1: fcitx_status(); press_any_key()
        elif choice == 2: fcitx_uninstall(); press_any_key()
        elif choice == 3: break

def deps_menu_loop() -> None:
    """Dependencies & Recommended apps submenu."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    while True:
        items = [
            MenuItem(label=msg("deps_sub_core")),
            MenuItem(label=msg("deps_sub_apps")),
            MenuItem(label=msg("deps_sub_back"), style="subtle"),
        ]
        menu = Menu("deps_menu_title", items, hint_key="submenu_hint")
        choice = menu.run()
        if choice == 0: run_dep_menu_loop(); press_any_key()
        elif choice == 1: run_optional_apps_menu_loop(); press_any_key()
        elif choice == 2: break

def optional_modules_menu_loop() -> None:
    """Optional modules interactive submenu."""
    while True:
        label0 = pad_display(msg("optmod_sub_apps"), 26)
        label1 = pad_display("Noctalia Greeter", 26) + greeter_status_label()
        label2 = pad_display(msg("optmod_sub_fcitx"), 26) + fcitx_status_label()
        label3 = pad_display(msg("optmod_sub_wallpapers"), 26) + (msg("status_wallpapers_installed") if wallpapers_pack_present() else msg("status_wallpapers_missing"))

        items = [
            MenuItem(label=label0),
            MenuItem(label=label1),
            MenuItem(label=label2),
            MenuItem(label=label3),
            MenuItem(label=msg("optmod_purge"), style="warn"),
            MenuItem(label=msg("optmod_back"), style="subtle"),
        ]
        menu = Menu("optmod_menu_title", items, hint_key="submenu_hint")
        choice = menu.run()
        if choice == 0: run_optional_apps_menu_loop()
        elif choice == 1: greeter_menu_loop()
        elif choice == 2: fcitx_menu_loop()
        elif choice == 3: deploy_wallpapers(do_download=True); press_any_key()
        elif choice == 4: uninstall_nyxniri("purge"); press_any_key()
        elif choice == 5: break

def main_menu_loop() -> None:
    """Main NyxNiri control panel interactive loop."""
    env = get_env()
    while True:
        items = [
            MenuItem(label=msg("menu_opt1"), group_header=msg("menu_group_deploy")),
            MenuItem(label=msg("menu_opt2")),
            MenuItem(label=msg("menu_opt3"), group_header=msg("menu_group_maint")),
            MenuItem(label=msg("menu_opt4")),
            MenuItem(label=msg("menu_opt5")),
            MenuItem(label=msg("menu_opt6")),
            MenuItem(label=msg("menu_opt7"), group_header=msg("menu_group_system"), style="warn"),
            MenuItem(label=msg("menu_opt8")),
            MenuItem(label=msg("menu_opt0"), style="subtle"),
        ]
        menu = Menu("menu_title", items, hint_key="menu_hint")
        choice = menu.run()

        if choice == 0:
            install_configs_workflow("full")
        elif choice == 1:
            deps_menu_loop()
        elif choice == 2:
            snapshot_menu_loop()
        elif choice == 3:
            update_result = safe_git_pull(env.repo_dir)
            if update_result is True:
                offer_overwrite_upgrade()
                check_new_deps_post_update()
                print(msg("updating_done"))
                press_any_key()
                # Re-exec to load new code
                os.execv(sys.executable, [sys.executable, "-m", "nyxniri"])
            elif update_result is False:
                print(msg("updating_failed"), file=sys.stderr)
            press_any_key()
        elif choice == 4:
            run_doctor()
            press_any_key()
        elif choice == 5:
            generate_bug_report()
            press_any_key()
        elif choice == 6:
            uninstall_nyxniri("")
            press_any_key()
        elif choice == 7:
            optional_modules_menu_loop()
        elif choice == 8:
            sys.exit(0)

# --- CLI Dispatcher ---
def print_help(file=None) -> None:
    """Print standard CLI help and commands overview."""
    if file is None:
        file = sys.stdout
    print(msg("cli_help", PROJECT_NAME, CLI_CMD), file=file)


def exit_usage(usage: str) -> None:
    """Report invalid arguments and exit without entering the interactive flow."""
    print(msg("err_invalid_args", usage), file=sys.stderr)
    sys.exit(2)


# --- Command Handlers ---
# Each handler receives (sub_args: List[str]) and returns an int exit code.
# Adding a new command = write a handler + add one line to COMMANDS.

def _cmd_install(sub_args: List[str]) -> int:
    mode = sub_args[0] if sub_args else "full"
    if len(sub_args) > 1 or mode not in ("full", "config"):
        exit_usage(f"{CLI_CMD} install [full|config]")
    return 0 if install_configs_workflow(mode) else 1

def _cmd_snapshot(sub_args: List[str]) -> int:
    if sub_args and sub_args[0] in ("delete", "rm"):
        if len(sub_args) > 2:
            exit_usage(f"{CLI_CMD} snapshot delete [index]")
        target = sub_args[1] if len(sub_args) > 1 else ""
        return 0 if delete_backup(target) else 1
    note = " ".join(sub_args)
    return 0 if backup_configs(note=note, interactive=False) else 1

def _cmd_rollback(sub_args: List[str]) -> int:
    if len(sub_args) > 1:
        exit_usage(f"{CLI_CMD} rollback [index]")
    target = sub_args[0] if sub_args else ""
    return 0 if rollback_configs(target) else 1

def _cmd_list(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} list")
    list_backups()
    return 0

def _cmd_uninstall(sub_args: List[str]) -> int:
    target = sub_args[0] if sub_args else ""
    if len(sub_args) > 1 or target not in ("", "standard", "restore", "purge"):
        exit_usage(f"{CLI_CMD} uninstall [standard|restore|purge]")
    return 0 if uninstall_nyxniri(target) else 1

def _cmd_purge(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} purge")
    return 0 if uninstall_nyxniri("purge") else 1

def _cmd_doctor(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} doctor")
    run_doctor()
    return 0

def _cmd_deps(sub_args: List[str]) -> int:
    sub = sub_args[0].lower() if sub_args else ""
    if len(sub_args) > 1 or sub not in ("", "core", "apps", "opt", "optional"):
        exit_usage(f"{CLI_CMD} deps [core|apps]")
    if sub == "core":
        run_dep_menu_loop()
    elif sub in ("apps", "opt", "optional"):
        run_optional_apps_menu_loop()
    else:
        deps_menu_loop()
    return 0

def _cmd_apps(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} apps")
    run_optional_apps_menu_loop()
    return 0

def _cmd_wallpapers(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} wallpapers")
    wallpaper_result = deploy_wallpapers(do_download=True)
    return 0 if wallpaper_result.downloaded else 1

def _cmd_bug(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} bug")
    generate_bug_report()
    return 0

def _cmd_test(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} test")
    return 0 if test_deploy() else 1

def _module_handler(module_name: str, triad_name: str):
    """Factory: build a handler for install|status|uninstall triad (greeter/fcitx).

    Looks up functions lazily from the module so patches in tests take effect.
    """
    def handler(sub_args: List[str]) -> int:
        import importlib
        mod = importlib.import_module(f"nyxniri.{module_name}")
        install_fn = getattr(mod, f"{module_name}_install")
        uninstall_fn = getattr(mod, f"{module_name}_uninstall")
        status_fn = getattr(mod, f"{module_name}_status")
        sub = sub_args[0].lower() if sub_args else ""
        if len(sub_args) > 1 or sub not in ("", "install", "setup", "status", "uninstall", "remove"):
            exit_usage(f"{CLI_CMD} {triad_name} [install|status|uninstall]")
        if sub in ("install", "setup"):
            return 0 if install_fn() else 1
        elif sub in ("uninstall", "remove"):
            return 0 if uninstall_fn() else 1
        else:
            status_fn()
            return 0
    return handler

def _cmd_theme(sub_args: List[str]) -> int:
    sub = sub_args[0] if sub_args else "toggle"
    if len(sub_args) > 1 or sub not in ("toggle", "dark", "light", "sync", "status"):
        exit_usage(f"{CLI_CMD} theme [toggle|dark|light|sync|status]")
    env = get_env()
    sync_script = env.config_dir / THEME_ENGINE / "theme-sync.sh"
    if not sync_script.is_file() and (env.configs_src / THEME_ENGINE / "theme-sync.sh").is_file():
        sync_script = env.configs_src / THEME_ENGINE / "theme-sync.sh"
    if sync_script.is_file():
        try:
            sync_script.chmod(0o755)
        except Exception:
            pass
        res = subprocess.run(["bash", str(sync_script), sub], check=False)
        return res.returncode
    else:
        print(msg("err_theme_sync_missing"), file=sys.stderr)
        return 1

def _cmd_update(sub_args: List[str]) -> int:
    flag = sub_args[0] if sub_args else ""
    if len(sub_args) > 1 or flag not in ("", "--force", "--deploy", "--no-deploy"):
        exit_usage(f"{CLI_CMD} update [--force|--no-deploy]")
    env = get_env()
    update_result = safe_git_pull(env.repo_dir)
    if update_result is True:
        deploy_ok = offer_overwrite_upgrade(flag)
        check_new_deps_post_update()
        print(msg("updating_done"))
        return 0 if deploy_ok else 1
    if update_result is False:
        print(msg("updating_failed"), file=sys.stderr)
        return 1
    return 0

def _cmd_preset(sub_args: List[str]) -> int:
    if not sub_args:
        print("Usage:")
        print(f"  {CLI_CMD} preset list [config]")
        print(f"  {CLI_CMD} preset set <config> <preset>")
        print(f"  {CLI_CMD} preset apply [config]")
        return 0
    sub = sub_args[0].lower()
    if sub == "list":
        items = sub_args[1:] if len(sub_args) > 1 else discover_config_items()
        for item in items:
            presets = list_presets(item)
            active = get_active_preset(item)
            if not presets:
                continue
            print(f"{item}:")
            for p in presets:
                marker = " *" if p == active else ""
                print(f"  {p}{marker}")
            if not active:
                print(f"  (default)")
        return 0
    elif sub == "set":
        if len(sub_args) != 3:
            exit_usage(f"{CLI_CMD} preset set <config> <preset>")
        config_item, preset_name = sub_args[1], sub_args[2]
        if not set_preset(config_item, preset_name):
            print(f"Preset not found: {config_item}/{preset_name}", file=sys.stderr)
            return 1
        print(f"Preset set: {config_item} -> {preset_name}")
        return 0
    elif sub == "apply":
        items = sub_args[1:] if len(sub_args) > 1 else discover_config_items()
        ok = True
        for item in items:
            if not apply_preset(item):
                print(f"Failed to apply preset for: {item}", file=sys.stderr)
                ok = False
        return 0 if ok else 1
    else:
        exit_usage(f"{CLI_CMD} preset [list|set|apply]")
        return 1

def _cmd_help(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} help")
    print_help()
    return 0


COMMANDS = {
    "install":   (_cmd_install,   f"{CLI_CMD} install [full|config]"),
    "deploy":    (_cmd_install,   f"{CLI_CMD} install [full|config]"),
    "snapshot":  (_cmd_snapshot,  f"{CLI_CMD} snapshot [note]"),
    "backup":    (_cmd_snapshot,  f"{CLI_CMD} snapshot [note]"),
    "rollback":  (_cmd_rollback,  f"{CLI_CMD} rollback [index]"),
    "restore":   (_cmd_rollback,  f"{CLI_CMD} rollback [index]"),
    "list":      (_cmd_list,      f"{CLI_CMD} list"),
    "uninstall": (_cmd_uninstall, f"{CLI_CMD} uninstall [standard|restore|purge]"),
    "remove":    (_cmd_uninstall, f"{CLI_CMD} uninstall [standard|restore|purge]"),
    "purge":     (_cmd_purge,     f"{CLI_CMD} purge"),
    "doctor":    (_cmd_doctor,    f"{CLI_CMD} doctor"),
    "deps":      (_cmd_deps,      f"{CLI_CMD} deps [core|apps]"),
    "apps":      (_cmd_apps,      f"{CLI_CMD} apps"),
    "recommended": (_cmd_apps,    f"{CLI_CMD} apps"),
    "wallpapers": (_cmd_wallpapers, f"{CLI_CMD} wallpapers"),
    "wp":        (_cmd_wallpapers, f"{CLI_CMD} wallpapers"),
    "bug":       (_cmd_bug,       f"{CLI_CMD} bug"),
    "report":    (_cmd_bug,       f"{CLI_CMD} bug"),
    "test":      (_cmd_test,      f"{CLI_CMD} test"),
    "greeter":   (_module_handler("greeter", "greeter"),
                  f"{CLI_CMD} greeter [install|status|uninstall]"),
    "fcitx":     (_module_handler("fcitx", "fcitx"),
                  f"{CLI_CMD} fcitx [install|status|uninstall]"),
    "gtk":       (_module_handler("gtktheme", "gtk"),
                  f"{CLI_CMD} gtk [install|status|uninstall]"),
    "theme":     (_cmd_theme,     f"{CLI_CMD} theme [toggle|dark|light|sync|status]"),
    "preset":    (_cmd_preset,    f"{CLI_CMD} preset [list|set <config> <preset>|apply]"),
    "update":    (_cmd_update,    f"{CLI_CMD} update [--force|--no-deploy]"),
    "help":      (_cmd_help,      f"{CLI_CMD} help"),
    "-h":        (_cmd_help,      f"{CLI_CMD} help"),
    "--help":    (_cmd_help,      f"{CLI_CMD} help"),
}

def main() -> None:
    """Main CLI entrypoint."""
    if os.getuid() == 0:
        print(msg("err_root_denied"), file=sys.stderr)
        sys.exit(1)

    acquire_lock()
    init_logger()
    get_env()
    ensure_nyxniri_symlink()

    args = sys.argv[1:]
    if args:
        cmd = args[0].lower()
        sub_args = args[1:]

        entry = COMMANDS.get(cmd)
        if entry:
            handler, _ = entry
            sys.exit(handler(sub_args))

        print(msg("err_unknown_command", args[0]), file=sys.stderr)
        print_help(file=sys.stderr)
        sys.exit(2)

    # Interactive flow
    if not sys.stdin.isatty():
        sys.exit(0 if install_configs_workflow("full") else 1)
    select_language()
    main_menu_loop()

if __name__ == "__main__":
    main()
