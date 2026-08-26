"""Environment context: path resolution and run-mode detection."""
import os
import subprocess
from pathlib import Path
from typing import Optional
from nyxniri.constants import ASSETS_DIR_NAME, CONFIG_DIR_NAME, PROJECT_NAME
from nyxniri.version import get_version


class Environment:
    def __init__(self):
        self.home = Path(os.environ.get("HOME", str(Path.home())))
        self.state_dir = Path(os.environ.get("XDG_STATE_HOME", str(self.home / ".local/state"))) / PROJECT_NAME
        self.cache_dir = self.home / ".cache" / PROJECT_NAME
        self.config_dir = self.home / ".config"
        current_file = Path(__file__).resolve()
        pkg_dir = current_file.parent
        root_dir = pkg_dir.parent
        if root_dir.resolve() == self.cache_dir.resolve():
            self.run_mode = "standalone"
            self.mode_label = "Remote Cache"
            self.repo_dir = self.cache_dir
        elif (root_dir / CONFIG_DIR_NAME).is_dir() and (root_dir / ASSETS_DIR_NAME).is_dir():
            self.run_mode = "repo"
            self.mode_label = "Local Path"
            self.repo_dir = root_dir
        else:
            self.run_mode = "standalone"
            self.mode_label = "Remote Cache"
            self.repo_dir = self.cache_dir
        self.configs_src = self.repo_dir / CONFIG_DIR_NAME
        self.assets_src = self.repo_dir / ASSETS_DIR_NAME
        self.version = get_version(self.repo_dir)


_ENV: Optional[Environment] = None

def get_env() -> Environment:
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV


_PICS_DIR_CACHE: Optional[Path] = None

def get_pics_dir() -> Path:
    global _PICS_DIR_CACHE
    if _PICS_DIR_CACHE is not None:
        return _PICS_DIR_CACHE
    home = get_env().home
    try:
        res = subprocess.run(
            ["xdg-user-dir", "PICTURES"],
            capture_output=True, text=True, check=False,
            env={**os.environ, "LC_ALL": "C"}
        )
        d = res.stdout.strip()
        if d and d != str(home):
            _PICS_DIR_CACHE = Path(d)
            return _PICS_DIR_CACHE
    except Exception:
        pass
    _PICS_DIR_CACHE = home / "Pictures"
    return _PICS_DIR_CACHE
