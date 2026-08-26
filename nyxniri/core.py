"""Core runtime facade: re-exports from split submodules."""
from nyxniri.env import Environment, get_env, get_pics_dir
from nyxniri.lock import acquire_lock, release_lock
from nyxniri.log import init_logger, log_msg
from nyxniri.cleanup import register_temp_path, cleanup_temp_paths
from nyxniri.symlink import ensure_nyxniri_symlink
from nyxniri.version import get_version
