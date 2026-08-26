"""Rolling log engine for NyxNiri."""
import datetime
import re
from pathlib import Path
from typing import Optional
from nyxniri.constants import PROJECT_NAME
from nyxniri.env import get_env

_LOG_FILE: Optional[Path] = None
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def init_logger() -> None:
    global _LOG_FILE
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = env.state_dir / "install.log"
    if _LOG_FILE.is_file():
        try:
            lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > 800:
                _LOG_FILE.write_text("\n".join(lines[-800:]) + "\n", encoding="utf-8")
        except Exception:
            pass
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"{now} [INFO] {PROJECT_NAME} Session Started ({env.version}) [mode: {env.mode_label}]\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception:
        pass

def log_msg(level: str, message: str) -> None:
    if _LOG_FILE is None:
        return
    clean_text = ANSI_ESCAPE_RE.sub("", message)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} [{level}] {clean_text}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
