"""Configuration snapshot, backup, rollback, and uninstallation management."""

import datetime
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from nyxniri.constants import CLI_CMD, Colors, PROJECT_NAME
from nyxniri.core import (
    get_env,
    get_pics_dir,
    log_msg,
    register_temp_path,
)
from nyxniri.i18n import msg
from nyxniri.tui import CheckboxEntry, CheckboxList, prompt_confirm, truncate_display


_MANAGED_SNAPSHOT_RE = re.compile(
    r"^(?:(?:snapshot|pre_rollback)_\d{8}_\d{6}(?:_\d+){0,2}|dotfiles_backup_.+)$"
)


def _copy_path(src: Path, dest: Path) -> None:
    """Copy one path while preserving a top-level symlink as a symlink."""
    if src.is_symlink():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        dest.symlink_to(os.readlink(src))
    elif src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _remove_path(path: Path) -> None:
    """Remove a path without following a top-level symlink."""
    try:
        if path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def get_backup_base_dir() -> Path:
    """Resolve standard backup base directory ~/.config/NyxNiri/backups."""
    return get_env().config_dir / PROJECT_NAME / "backups"


def backup_configs(note: str = "", interactive: bool = True) -> Optional[Path]:
    """Create a complete snapshot of all active dotfiles configurations."""
    from nyxniri.deploy import discover_config_items

    env = get_env()
    base_dir = get_backup_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    print(msg("backing_up"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = base_dir / f"snapshot_{timestamp}"
    suffix = 1
    while backup_dir.exists() or backup_dir.is_symlink():
        backup_dir = base_dir / f"snapshot_{timestamp}_{suffix}"
        suffix += 1

    tmp_dir = Path(tempfile.mkdtemp(prefix=".snapshot.", dir=base_dir))
    register_temp_path(tmp_dir)

    items = discover_config_items()
    for item in items:
        cfg_path = env.config_dir / item
        if cfg_path.exists() or cfg_path.is_symlink():
            target = tmp_dir / item
            _copy_path(cfg_path, target)
            print(msg("log_backup_item", item))

    if note.strip():
        (tmp_dir / "note.txt").write_text(note.strip(), encoding="utf-8")

    tmp_dir.rename(backup_dir)
    print(msg("backup_done", str(backup_dir)))
    log_msg("INFO", f"Created configuration snapshot at {backup_dir}")
    return backup_dir


def get_all_backups() -> List[Path]:
    """Discover all snapshot directories including legacy dotfiles_backup_* folders."""
    env = get_env()
    base_dir = get_backup_base_dir()
    backups: List[Path] = []

    if base_dir.is_dir():
        for d in base_dir.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    # Legacy snapshots directly under ~/.config/
    if env.config_dir.is_dir():
        for d in env.config_dir.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    return sorted(backups, key=lambda p: p.name)


def _resolve_backup_arg(target_arg: str, backups: List[Path]) -> Optional[Path]:
    """Resolve a CLI snapshot argument only against discovered snapshot paths."""
    value = target_arg.strip()
    if not value:
        return None
    if value.isdigit():
        idx = int(value) - 1
        return backups[idx] if 0 <= idx < len(backups) else None
    try:
        candidate = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    for backup in backups:
        try:
            if candidate == backup.resolve(strict=True):
                return backup
        except (OSError, RuntimeError):
            continue
    return None


def _read_snapshot_note(backup: Path) -> str:
    """Read a note for display without allowing terminal control characters."""
    note_file = backup / "note.txt"
    if not note_file.is_file():
        return ""
    try:
        raw = note_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in raw).split())
    return truncate_display(text, 50, suffix="...")


def _snapshot_label(index: int, backup: Path) -> str:
    """Build a compact selectable label with an optional user note."""
    note = _read_snapshot_note(backup)
    suffix = f" - {note}" if note else ""
    return f"[{index}] {backup.name}{suffix}"


def list_backups() -> List[Path]:
    """Display a numbered list of all available snapshots."""
    backups = get_all_backups()
    if not backups:
        print(msg("no_backups_found"))
        return []

    print(msg("available_backups"))
    for idx, b in enumerate(backups, start=1):
        note = _read_snapshot_note(b)
        note_str = f" {Colors.DARK_GRAY}— {note}{Colors.RESET}" if note else ""
        print(f"  {Colors.BOLD_CYAN}[{idx}]{Colors.RESET} {Colors.BOLD_WHITE}{b.name}{Colors.RESET}{note_str}")
        print(f"      {Colors.DARK_GRAY}{b}{Colors.RESET}")
    print()
    return backups


def rollback_configs(target_arg: str = "") -> bool:
    """Restore configuration from a selected historical snapshot."""
    from nyxniri.deploy import atomic_replace_item, discover_config_items

    backups = list_backups()
    if not backups:
        return False

    chosen_backup = _resolve_backup_arg(target_arg, backups)
    if target_arg.strip() and chosen_backup is None:
        print(msg("rollback_invalid_num"))
        return False

    if chosen_backup is None:
        if not sys.stdin.isatty():
            print(msg("rollback_invalid_num"))
            return False
        try:
            sys.stdout.write(msg("select_rollback_target"))
            sys.stdout.flush()
            val = sys.stdin.readline().strip()
            if not val.isdigit() or not (1 <= int(val) <= len(backups)):
                print(msg("rollback_invalid_num"))
                return False
            chosen_backup = backups[int(val) - 1]
        except Exception:
            return False

    print(msg("rolling_back", chosen_backup.name))

    # Auto pre-rollback snapshot
    pre_snap = backup_configs(note="pre_rollback_backup", interactive=False)
    if pre_snap:
        print(msg("pre_rollback_backup", str(pre_snap)))

    env = get_env()
    items = discover_config_items()
    for item in items:
        snap_item = chosen_backup / item
        dest_item = env.config_dir / item
        if snap_item.exists() or snap_item.is_symlink():
            if not atomic_replace_item(snap_item, dest_item):
                print(msg("log_deploy_config_failed", item), file=sys.stderr)
                log_msg("ERROR", f"Failed to restore snapshot item {snap_item}")
                return False
            print(msg("log_restore_item", item))

    print(msg("rollback_done", chosen_backup.name))
    log_msg("INFO", f"Rolled back dotfiles from snapshot {chosen_backup}")
    return True


def delete_backup(target_arg: str = "") -> bool:
    """Delete one or more configuration snapshots after explicit confirmation."""
    backups = get_all_backups()
    if not backups:
        print(msg("no_backups_found"))
        return False

    selected: List[Path] = []
    if target_arg.strip():
        chosen_backup = _resolve_backup_arg(target_arg, backups)
        if chosen_backup is None:
            print(msg("delete_invalid_num"))
            return False
        selected = [chosen_backup]
    elif sys.stdin.isatty():
        entries = [
            CheckboxEntry(key=str(index), label=_snapshot_label(index, backup))
            for index, backup in enumerate(backups, start=1)
        ]
        chosen_keys = CheckboxList(
            "delete_snapshot_title", entries, hint_key="delete_snapshot_hint"
        ).run()
        if chosen_keys is None:
            print(msg("delete_cancelled"))
            return False
        selected = [backups[int(key) - 1] for key in chosen_keys]
    else:
        print(msg("delete_invalid_num"))
        return False

    if not selected:
        print(msg("delete_none_selected"))
        return False

    if len(selected) == 1:
        print(msg("delete_confirm", selected[0].name))
    else:
        print(msg("delete_confirm_many", len(selected)))
        for backup in selected:
            print(f"    {backup.name}")
    if not prompt_confirm("delete_prompt", "n"):
        print(msg("delete_cancelled"))
        return False

    deleted: List[Path] = []
    for backup in selected:
        try:
            shutil.rmtree(backup)
            deleted.append(backup)
        except OSError as exc:
            print(msg("delete_failed", backup.name), file=sys.stderr)
            log_msg("ERROR", f"Failed to delete snapshot {backup}: {exc}")

    if not deleted:
        return False
    remaining = len(get_all_backups())
    if len(deleted) == 1:
        print(msg("delete_done", deleted[0].name, remaining))
    else:
        print(msg("delete_done_many", len(deleted), remaining))
    for backup in deleted:
        log_msg("INFO", f"Deleted snapshot {backup}")
    return len(deleted) == len(selected)

def uninstall_nyxniri(mode: str = "") -> bool:
    """Safely uninstall NyxNiri or deep purge configurations and cache."""
    from nyxniri.deploy import discover_config_items
    from nyxniri.greeter import greeter_uninstall

    env = get_env()
    items = discover_config_items()

    if not mode and not sys.stdin.isatty():
        print(msg("uninstall_interactive_required"))
        return False

    if not mode and sys.stdin.isatty():
        print(msg("uninstall_title"))
        print(f"  {Colors.BOLD_GREEN}1){Colors.RESET} {msg('uninstall_opt1')}")
        print(f"  {Colors.BOLD_CYAN}2){Colors.RESET} {msg('uninstall_opt2')}")
        print(f"  {Colors.BOLD_RED}3){Colors.RESET} {msg('uninstall_opt3')}")
        print(f"  {Colors.DARK_GRAY}4){Colors.RESET} {msg('uninstall_opt4')}\n")
        try:
            sys.stdout.write("▸ [1-4]: ")
            sys.stdout.flush()
            choice = sys.stdin.readline().strip()
            if choice == "1": mode = "standard"
            elif choice == "2": mode = "restore"
            elif choice == "3": mode = "purge"
            else:
                print(msg("log_uninstall_cancelled"))
                return False
        except Exception:
            return False

    if mode == "purge":
        print(msg("purge_warning"))
        if not prompt_confirm("purge_prompt", "n"):
            print(msg("purge_cancelled"))
            return False
        print(msg("purge_start"))
        try:
            fcitx_uninstall()
        except Exception:
            pass
        try:
            greeter_uninstall()
        except Exception:
            pass

        for item in items:
            p = env.config_dir / item
            if p.exists() or p.is_symlink():
                _remove_path(p)
                print(msg("log_remove_item", item))

        for backup in get_all_backups():
            _remove_path(backup)

        _remove_path(env.config_dir / PROJECT_NAME)
        _remove_path(env.state_dir)
        _remove_path(env.cache_dir)

        pics_wp = get_pics_dir() / "Wallpapers"
        _remove_path(pics_wp)

        target_bin = env.home / ".local/bin" / CLI_CMD
        target_bin.unlink(missing_ok=True)
        print(msg("purge_done"))
        return True

    if mode == "restore":
        backups = get_all_backups()
        if not backups:
            print(msg("no_backups_found"))
            return False
        origin = backups[0]
        print(msg("log_restoring_origin_config", origin.name))
        rollback_configs(str(origin))
        print(msg("restore_origin_done"))
        return True

    # Standard uninstall: Archive current dotfiles, remove configs & CLI
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = env.config_dir / f"{PROJECT_NAME}_archive_{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for item in items:
        p = env.config_dir / item
        if p.exists() or p.is_symlink():
            target = archive_dir / item
            _copy_path(p, target)
            _remove_path(p)
            print(msg("log_remove_item", item))

    target_bin = env.home / ".local/bin" / CLI_CMD
    target_bin.unlink(missing_ok=True)

    from nyxniri.fcitx import fcitx_uninstall as _fcitx_cleanup
    try:
        _fcitx_cleanup()
    except Exception:
        pass

    print(msg("uninstall_archived", str(archive_dir)))
    print(msg("uninstall_done"))
    log_msg("INFO", f"Uninstalled NyxNiri (archived to {archive_dir})")
    return True
