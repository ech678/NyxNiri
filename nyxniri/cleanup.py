"""Temporary path registry and cleanup on process exit."""
import atexit
import shutil
from pathlib import Path

_CLEANUP_TEMP_PATHS: set[Path] = set()

def register_temp_path(path: Path | str) -> None:
    if path:
        _CLEANUP_TEMP_PATHS.add(Path(path))

def cleanup_temp_paths() -> None:
    for p in list(_CLEANUP_TEMP_PATHS):
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists() or p.is_symlink():
                p.unlink(missing_ok=True)
        except Exception:
            pass
    _CLEANUP_TEMP_PATHS.clear()

atexit.register(cleanup_temp_paths)
