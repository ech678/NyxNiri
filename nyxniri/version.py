"""Dynamic version extraction from changelog or git tags."""
import re
import subprocess
from pathlib import Path
import os

_VERSION_CACHE: str = ""

def get_version(target_dir: Path) -> str:
    global _VERSION_CACHE
    if _VERSION_CACHE:
        return _VERSION_CACHE
    changelog = target_dir / "CHANGELOG.md"
    if changelog.is_file():
        try:
            content = changelog.read_text(encoding="utf-8")
            for candidate in re.findall(r"^##\s+\[([^\]]+)\]", content, re.MULTILINE):
                if candidate.lower() != "unreleased":
                    _VERSION_CACHE = candidate
                    return _VERSION_CACHE
        except Exception:
            pass
    if (target_dir / ".git").is_dir():
        try:
            res = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=target_dir, capture_output=True, text=True, check=False,
                env={**os.environ, "LC_ALL": "C"}
            )
            v = res.stdout.strip()
            if v:
                _VERSION_CACHE = v
                return _VERSION_CACHE
        except Exception:
            pass
    _VERSION_CACHE = "v3.0.0"
    return _VERSION_CACHE
