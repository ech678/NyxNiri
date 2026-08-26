"""Global constants, paths, URLs, and color palettes for NyxNiri."""

import os
from pathlib import Path

# --- Project Identity ---
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

# --- Directory Constants ---
CONFIG_DIR_NAME = "configs"
ASSETS_DIR_NAME = "assets"

# --- Repository & Network Mirrors ---
REPO_URL = "https://github.com/ech678/NyxNiri.git"

GIT_MIRROR_REGISTRY = [
    ("Official", "https://github.com/ech678/NyxNiri.git"),
    ("gh-proxy.org", "https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"),
]

RAW_MIRROR_TEMPLATES = [
    ("Official", "https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
    ("jsDelivr-CDN", "https://fastly.jsdelivr.net/gh/{USER_REPO}@{BRANCH}/{FILE_PATH}"),
    ("gh-proxy.org", "https://gh-proxy.org/https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
]

WALLPAPER_MIRRORS = [
    ("Official", "https://github.com/ech678/wallpaper-collection.git"),
    ("gh-proxy.org", "https://gh-proxy.org/https://github.com/ech678/wallpaper-collection.git"),
]

# --- Dependencies ---
CORE_DEPS = [
    MAIN_WM,
    THEME_ENGINE,
    "wlsunset",
    "fish",
    "starship",
    "kitty",
    "fastfetch",
    "eza",
    "mpvpaper",
    "ffmpeg",
    "jq",
    "tmux",
    "inotify-tools",
    "fzf",
    "python-gobject",
    "gtk-layer-shell",
    "ttf-jetbrains-mono",
    "ttf-jetbrains-mono-nerd",
    "noto-fonts-cjk",
]

AUR_DEPS = [
    "mpvpaper",
]

OPTIONAL_APPS = [
    "nautilus",
    "missioncenter",
    "fcitx5-rime",
    "nvidia-driver",
]

# --- Fedora Support ---
FEDORA_MIN_VERSION = 44

# RPM Fusion release RPMs to auto-install on Fedora (provides proprietary drivers like NVIDIA).
FEDORA_RPM_FUSION_REPOS = [
    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm",
    "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
]

# COPR repos to auto-enable on Fedora (name → copr handle).
FEDORA_COPR_REPOS = [
    ("nerd-fonts", "che/nerd-fonts"),
]

# Arch key → Fedora install descriptor.
# "method" ∈ {"dnf", "flatpak", "manual"}.
# "pkgs"   = dnf package names (empty for flatpak/manual).
# "flatpak"= flatpak app id (only when method == "flatpak").
# "build"  = build function name in deps.py (only when method == "manual").
FEDORA_PKG_MAP = {
    "niri":                  {"method": "dnf",    "pkgs": ["niri"]},
    "noctalia":              {"method": "dnf",    "pkgs": ["noctalia"]},
    "wlsunset":              {"method": "dnf",    "pkgs": ["wlsunset"]},
    "fish":                  {"method": "dnf",    "pkgs": ["fish"]},
    "starship":              {"method": "manual", "pkgs": [], "build": "build_starship"},
    "kitty":                 {"method": "dnf",    "pkgs": ["kitty"]},
    "fastfetch":             {"method": "dnf",    "pkgs": ["fastfetch"]},
    "eza":                   {"method": "dnf",    "pkgs": ["eza"]},
    "mpvpaper":              {"method": "manual", "pkgs": [], "build": "build_mpvpaper"},
    "ffmpeg":                {"method": "manual", "pkgs": [], "build": "build_ffmpeg"},
    "jq":                    {"method": "dnf",    "pkgs": ["jq"]},
    "tmux":                  {"method": "dnf",    "pkgs": ["tmux"]},
    "inotify-tools":         {"method": "dnf",    "pkgs": ["inotify-tools"]},
    "fzf":                   {"method": "dnf",    "pkgs": ["fzf"]},
    "python-gobject":        {"method": "dnf",    "pkgs": ["python3-gobject", "gobject-introspection"]},
    "gtk-layer-shell":       {"method": "dnf",    "pkgs": ["gtk-layer-shell", "gtk4-layer-shell"]},
    "ttf-jetbrains-mono":    {"method": "dnf",    "pkgs": ["jetbrains-mono-fonts-all"]},
    "ttf-jetbrains-mono-nerd": {"method": "dnf",  "pkgs": ["nerd-fonts"]},
    "noto-fonts-cjk":        {"method": "dnf",    "pkgs": ["google-noto-sans-cjk-fonts"]},
    # Optional apps
    "nautilus":              {"method": "dnf",    "pkgs": ["nautilus"]},
    "missioncenter":         {"method": "flatpak", "flatpak": "io.missioncenter.MissionCenter"},
    "fcitx5-rime":           {"method": "dnf",    "pkgs": [
        "fcitx5", "fcitx5-gtk2", "fcitx5-gtk3", "fcitx5-qt5", "fcitx5-qt6",
        "fcitx5-configtool", "fcitx5-rime",
    ]},
    # NVIDIA: needs RPM Fusion repo first, then akmod-nvidia (driver) + cuda (optional).
    "nvidia-driver":         {"method": "manual", "pkgs": [], "build": "build_nvidia_driver"},
}

# Fedora optional apps whose source needs COPR. None on Fedora = skip.
# (rime-ice-git has no Fedora equivalent; skipped silently.)
FEDORA_SKIP_APPS = {"rime-ice-git"}

# --- ANSI Styling Palette (NyxNiri Native) ---
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    DARK_GRAY = "\033[90m"

    # Bold Foreground colors
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_PURPLE = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_WHITE = "\033[1;37m"

    # Cursor controls
    CURSOR_HIDE = "\033[?25l"
    CURSOR_SHOW = "\033[?25h"
    CLEAR_SCREEN = "\033[H\033[J"
    CLEAR_LINE = "\033[2K\r"
