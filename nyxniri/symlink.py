"""CLI binary symlink management."""
from nyxniri.constants import CLI_CMD
from nyxniri.env import get_env

def ensure_nyxniri_symlink() -> None:
    env = get_env()
    bin_dir = env.home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_bin = bin_dir / CLI_CMD
    root_installer = env.repo_dir / "install.sh"
    if not root_installer.is_file():
        if (env.cache_dir / "install.sh").is_file():
            root_installer = env.cache_dir / "install.sh"
        else:
            return
    try:
        if not target_bin.is_symlink() or target_bin.resolve() != root_installer.resolve():
            target_bin.unlink(missing_ok=True)
            target_bin.symlink_to(root_installer)
            root_installer.chmod(0o755)
    except Exception:
        pass
