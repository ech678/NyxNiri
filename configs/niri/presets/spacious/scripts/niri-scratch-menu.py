#!/usr/bin/env python3
"""
NyxNiri Orbit Launcher (Legacy Compatibility Wrapper)
Forwards execution to orbit-launcher.py for seamless backward compatibility.
"""

import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_SCRIPT = os.path.join(SCRIPTS_DIR, "orbit-launcher.py")

if __name__ == "__main__":
    if os.path.isfile(TARGET_SCRIPT):
        os.execv(sys.executable, [sys.executable, TARGET_SCRIPT] + sys.argv[1:])
    else:
        # Fallback to direct import if file structure is flat
        if SCRIPTS_DIR not in sys.path:
            sys.path.insert(0, SCRIPTS_DIR)
        from orbit.window import OrbitLauncher
        from orbit.lock import acquire_instance_lock, release_instance_lock
        from gi.repository import Gtk
        import signal

        RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/nyxniri-{os.getuid()}"
        lock_fd = acquire_instance_lock(os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.lock"),
                                        os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.pid"))
        win = OrbitLauncher(lock_fd=lock_fd, pid_path=os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.pid"))
        signal.signal(signal.SIGINT, lambda s, f: win.dismiss_menu())
        signal.signal(signal.SIGTERM, lambda s, f: win.dismiss_menu())
        try:
            Gtk.main()
        finally:
            release_instance_lock(lock_fd, os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.pid"))
