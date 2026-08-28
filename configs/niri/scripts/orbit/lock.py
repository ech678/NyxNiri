"""
Orbit Launcher Single-Instance & True-Toggle Locking Engine
Ensures atomic single-instance execution. If another instance is running, sends SIGTERM to toggle-close it.
"""

import os
import sys
import signal
import fcntl

def _is_orbit_process(pid: int) -> bool:
    try:
        cmdline_path = f"/proc/{pid}/cmdline"
        if not os.path.isfile(cmdline_path):
            return False
        with open(cmdline_path, "rb") as f:
            cmdline = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
        return "orbit" in cmdline.lower() or "scratch" in cmdline.lower()
    except Exception:
        return False

def acquire_instance_lock(lock_path: str, pid_path: str) -> int:
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        if os.path.isfile(pid_path):
            try:
                with open(pid_path, "r") as pf:
                    raw = pf.read().strip()
                if not raw.isdigit():
                    sys.exit(0)
                old_pid = int(raw)
                if old_pid <= 1 or not _is_orbit_process(old_pid):
                    sys.exit(0)
                os.kill(old_pid, signal.SIGTERM)
            except Exception:
                pass
        sys.exit(0)
    try:
        with open(pid_path, "w") as pf:
            pf.write(str(os.getpid()))
    except Exception:
        pass
    return lock_fd

def release_instance_lock(lock_fd: int, pid_path: str):
    try:
        if os.path.isfile(pid_path):
            os.remove(pid_path)
    except Exception:
        pass
    try:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except Exception:
        pass
