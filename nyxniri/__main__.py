"""Entry point for python3 -m nyxniri."""

import sys


def _run() -> int:
    try:
        from nyxniri.cli import main
        main()
    except ModuleNotFoundError as e:
        # A missing nyxniri.* module means the engine tree is mixed or partial
        # (typically an update interrupted mid-checkout). Fail with one clear
        # line instead of a traceback; anything else is a real bug — re-raise.
        if not (getattr(e, "name", "") or "").startswith("nyxniri"):
            raise
        try:
            from nyxniri.i18n import msg
            text = msg("err_engine_incomplete")
        except Exception:
            text = ("[✗] 引擎文件不完整或更新中途被打断。重新运行 install.sh 即可恢复。\n"
                    "[✗] Engine files are incomplete or an update was interrupted. Rerun install.sh.")
        print(text, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_run())
