import os
import sys
import json
import random
import subprocess
import time

STATE_DIR = os.path.expanduser("~/.local/state/noctalia/mpvpaper")
ASSIGNMENTS_FILE = os.path.join(STATE_DIR, "assignments.json")

def _write_mpvpaper_assignments(assignments: dict):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp_file = f"{ASSIGNMENTS_FILE}.tmp.{os.getpid()}"
        data = {
            "assignments": assignments,
            "launchedAsSystemd": {k: False for k in assignments}
        }
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_file, ASSIGNMENTS_FILE)
    except Exception as e:
        print(f"Warning: Failed to update mpvpaper assignments: {e}", file=sys.stderr)

def _wait_for_process_exit(name: str, timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1
            )
            if result.returncode != 0:
                return True
        except Exception:
            return True
        time.sleep(0.05)
    return False

def _clear_mpvpaper():
    try:
        subprocess.run(
            ["noctalia", "msg", "plugin", "noctalia/mpvpaper:service", "all", "clear-all"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )
    except Exception:
        pass
    _write_mpvpaper_assignments({})
    subprocess.run(["pkill", "-x", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _wait_for_process_exit("mpvpaper", timeout=2.0)

def apply_static_wallpaper(path: str) -> bool:
    try:
        _clear_mpvpaper()
        subprocess.Popen(["noctalia", "msg", "wallpaper-set", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error applying static wallpaper: {e}", file=sys.stderr)
        return False

def apply_dynamic_wallpaper(video_path: str, thumb_path: str = None) -> bool:
    try:
        _clear_mpvpaper()
        _write_mpvpaper_assignments({"*": video_path})
        if thumb_path and os.path.isfile(thumb_path):
            subprocess.run(
                ["noctalia", "msg", "wallpaper-set", thumb_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
            )
        time.sleep(0.15)
        hook_script = os.path.expanduser("~/.config/noctalia/mpv-hook.lua")
        mpv_opts = "loop-file=inf panscan=1.0 no-audio hwdec=auto"
        if os.path.isfile(hook_script):
            mpv_opts += f" --script={hook_script}"
        cmd = ["mpvpaper", "--auto-pause", "-o", mpv_opts, "*", video_path]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error applying live wallpaper: {e}", file=sys.stderr)
        return False

def apply_wallpaper(item) -> bool:
    if item.is_video:
        return apply_dynamic_wallpaper(item.path, item.thumb_path)
    else:
        return apply_static_wallpaper(item.path)

def apply_random_wallpaper(items: list):
    if not items:
        return None
    target = random.choice(items)
    apply_wallpaper(target)
    return target
