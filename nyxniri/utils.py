"""Shared utility helpers used across NyxNiri modules."""
import os
import shutil
from pathlib import Path
from nyxniri.i18n import get_lang


def _text(zh: str, en: str) -> str:
    return zh if get_lang() == "zh" else en


def _remove_path(path: Path) -> None:
    try:
        if path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def _copy_path(src: Path, dest: Path) -> None:
    if src.is_symlink():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        dest.symlink_to(os.readlink(src))
    elif src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
