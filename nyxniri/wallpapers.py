"""Wallpaper pack deployment and offline fallback sync."""
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from nyxniri.constants import WALLPAPER_MIRRORS
from nyxniri.env import get_env, get_pics_dir
from nyxniri.log import log_msg
from nyxniri.cleanup import register_temp_path
from nyxniri.i18n import msg
from nyxniri.network import git_clone_timeout


@dataclass(frozen=True)
class WallpaperDeployResult:
    download_attempted: bool
    downloaded: bool
    pack_present: bool
    fallback_synced: bool

    @property
    def download_failed(self) -> bool:
        return self.download_attempted and not self.downloaded


def _wallpaper_pack_present_at(root: Path) -> bool:
    video_dir = root / "video"
    try:
        return video_dir.is_dir() and any(path.is_file() for path in video_dir.rglob("*"))
    except OSError:
        return False


def wallpapers_pack_present() -> bool:
    return _wallpaper_pack_present_at(get_pics_dir() / "Wallpapers")


def deploy_wallpapers(do_download: bool = False) -> WallpaperDeployResult:
    wp_dest = get_pics_dir() / "Wallpapers"
    wp_dest.mkdir(parents=True, exist_ok=True)
    env = get_env()
    downloaded = False
    fallback_synced = False
    if do_download:
        print(msg("msg_downloading_wallpapers"))
        if not shutil.which("git"):
            failure_key = "msg_wallpapers_refresh_failed" if wallpapers_pack_present() else "msg_wallpapers_download_failed"
            print(msg(failure_key))
            log_msg("WARN", "Wallpaper pack download skipped: git not installed")
        else:
            tmp_clone = Path(tempfile.mkdtemp())
            register_temp_path(tmp_clone)
            success = False
            for idx, (tag, url) in enumerate(WALLPAPER_MIRRORS, start=1):
                print(msg("msg_downloading_wallpapers_node", f"{idx}/{len(WALLPAPER_MIRRORS)}", tag))
                if git_clone_timeout(url, tmp_clone, cancellable=sys.stdin.isatty()):
                    if _wallpaper_pack_present_at(tmp_clone):
                        success = True
                        break
                    log_msg("WARN", f"Wallpaper mirror [{tag}] returned an incomplete pack")
                shutil.rmtree(tmp_clone, ignore_errors=True)
            if success:
                shutil.rmtree(tmp_clone / ".git", ignore_errors=True)
                (tmp_clone / "preview.webp").unlink(missing_ok=True)
                (tmp_clone / "README.md").unlink(missing_ok=True)
                for item in tmp_clone.iterdir():
                    target = wp_dest / item.name
                    if target.exists():
                        continue
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)
                downloaded = True
                print(msg("msg_wallpapers_download_success"))
                log_msg("INFO", f"Wallpaper pack deployed to {wp_dest}")
                shutil.rmtree(tmp_clone, ignore_errors=True)
            else:
                failure_key = "msg_wallpapers_refresh_failed" if wallpapers_pack_present() else "msg_wallpapers_download_failed"
                print(msg(failure_key))
                log_msg("WARN", "Wallpaper pack download failed on all mirrors")

    fallback_src = env.assets_src / "wallpapers"
    if fallback_src.is_dir():
        for f in fallback_src.iterdir():
            target = wp_dest / f.name
            if not target.exists():
                shutil.copy2(f, target)
        fallback_synced = True
        print(msg("log_sync_wallpapers", str(wp_dest)))

    return WallpaperDeployResult(
        download_attempted=do_download,
        downloaded=downloaded,
        pack_present=wallpapers_pack_present(),
        fallback_synced=fallback_synced,
    )
