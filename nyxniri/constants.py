"""Project identity constants for NyxNiri."""
from pathlib import Path
from nyxniri.colors import Colors
from nyxniri.urls import REPO_URL, GIT_MIRROR_REGISTRY, RAW_MIRROR_TEMPLATES, WALLPAPER_MIRRORS
from nyxniri.deps_list import CORE_DEPS, AUR_DEPS, OPTIONAL_APPS

PROJECT_NAME = "NyxNiri"
CLI_CMD = "nyxniri"
MAIN_WM = "niri"
MAIN_WM_HARDWARE_CONFIG = "monitor.kdl"
THEME_ENGINE = "noctalia"
GREETER_PKG = "noctalia-greeter"
GREETER_SESSION_BIN = "noctalia-greeter-session"
GREETER_ETC_CFG = Path("/etc/greetd/config.toml")
GREETER_POLKIT_RULE = Path(f"/etc/polkit-1/rules.d/50-{GREETER_PKG}.rules")
FCITX_THEME = "nyxmellow"
CONFIG_DIR_NAME = "configs"
ASSETS_DIR_NAME = "assets"
