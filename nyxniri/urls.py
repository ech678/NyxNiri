"""Repository URLs and network mirror registries."""

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
