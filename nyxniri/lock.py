"""Single-instance lock via fcntl.flock."""
import atexit
import fcntl
import os
import sys
from pathlib import Path
from typing import Optional
from nyxniri.constants import CLI_CMD
from nyxniri.env import get_env

_LOCK_FILE: Optional[Path] = None
_LOCK_FD: Optional[int] = None

def acquire_lock() -> None:
    global _LOCK_FILE, _LOCK_FD
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE = env.state_dir / f"{CLI_CMD}.lock"
    try:
        _LOCK_FD = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        pid = "unknown"
        try:
            content = _LOCK_FILE.read_text().strip()
            if content.isdigit():
                pid = content
        except Exception:
            pass
        from nyxniri.i18n import msg
        print(msg("err_already_running", pid), file=sys.stderr)
        sys.exit(1)
    try:
        os.ftruncate(_LOCK_FD, 0)
        os.write(_LOCK_FD, str(os.getpid()).encode())
    except Exception:
        pass

def release_lock() -> None:
    global _LOCK_FD, _LOCK_FILE
    if _LOCK_FD is not None:
        try:
            fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
            os.close(_LOCK_FD)
        except Exception:
            pass
        _LOCK_FD = None
    if _LOCK_FILE:
        try:
            _LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

atexit.register(release_lock)
