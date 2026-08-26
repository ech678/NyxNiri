"""TUI component and terminal presentation engine (Native ANSI + Standard Library)."""
import atexit
import os
import re
import select
import shutil
import signal
import sys
import termios
import threading
import time
import tty
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from nyxniri.constants import Colors
from nyxniri.core import Environment, get_env
from nyxniri.i18n import msg

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -\/]*[@-~]")

_terminal_size_cache: Optional[tuple] = None


def _get_terminal_size() -> tuple:
    global _terminal_size_cache
    if _terminal_size_cache is not None:
        return _terminal_size_cache
    size = shutil.get_terminal_size((80, 24))
    _terminal_size_cache = (size.columns, size.lines)
    return _terminal_size_cache


_winch_handlers: List[Callable] = []


def _on_sigwinch(signum, frame) -> None:
    global _terminal_size_cache
    _terminal_size_cache = None
    for h in _winch_handlers:
        try:
            h()
        except Exception:
            pass

try:
    signal.signal(signal.SIGWINCH, _on_sigwinch)
except (AttributeError, ValueError, OSError):
    pass


def _register_winch(handler: Callable) -> None:
    if handler not in _winch_handlers:
        _winch_handlers.append(handler)


def _unregister_winch(handler: Callable) -> None:
    try:
        _winch_handlers.remove(handler)
    except ValueError:
        pass

class TerminalGuard:
    _orig_attr: Optional[List[Any]] = None
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if cls._initialized:
            return
        if sys.stdin.isatty():
            try:
                cls._orig_attr = termios.tcgetattr(sys.stdin.fileno())
            except Exception:
                cls._orig_attr = None
            atexit.register(cls.restore)
            signal.signal(signal.SIGINT, cls._sig_handler)
            signal.signal(signal.SIGTERM, cls._sig_handler)
        cls._initialized = True

    @classmethod
    def restore(cls) -> None:
        if cls._orig_attr and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, cls._orig_attr)
            except Exception:
                pass
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()

    @classmethod
    def _sig_handler(cls, signum: int, frame: Any) -> None:
        cls.restore()
        sys.stdout.write("\n")
        sys.exit(130)

TerminalGuard.init()


def display_width(text: str) -> int:
    clean_text = ANSI_ESCAPE_RE.sub("", text)
    return sum(
        0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in clean_text
    )


def pad_display(text: str, width: int) -> str:
    curr = display_width(text)
    if curr < width:
        return text + (" " * (width - curr))
    return text


def truncate_display(text: str, width: int, suffix: str = "…") -> str:
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    suffix_width = display_width(suffix)
    content_width = max(0, width - suffix_width)
    output: List[str] = []
    used = 0
    pos = 0
    while pos < len(text):
        match = ANSI_ESCAPE_RE.match(text, pos)
        if match:
            output.append(match.group(0))
            pos = match.end()
            continue
        ch = text[pos]
        ch_width = 0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if used + ch_width > content_width:
            break
        output.append(ch)
        used += ch_width
        pos += 1
    reset = Colors.RESET if ANSI_ESCAPE_RE.search(text) else ""
    return "".join(output) + suffix + reset


def responsive_hint(key: str) -> str:
    cols, _ = _get_terminal_size()
    if cols >= 72:
        return msg(key)
    short = {
        "menu_hint": "menu_hint_short",
        "submenu_hint": "submenu_hint_short",
        "selective_hint": "checklist_hint_short",
        "delete_snapshot_hint": "checklist_hint_short",
        "dep_menu_hint": "checklist_hint_short",
        "opt_apps_menu_hint": "checklist_hint_short",
        "summary_action_hint": "summary_action_hint_short",
    }
    return msg(short.get(key, key))


def read_key() -> str:
    if not sys.stdin.isatty():
        return "ENTER"
    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        raw = os.read(fd, 1)
        if not raw:
            return "EOF"
        if raw == b"\x1b":
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready:
                raw += os.read(fd, 31)
        if raw == b"\x1b":
            return "ESC"
        if raw in (b"\x1b[A", b"\x1bOA"):
            return "UP"
        if raw in (b"\x1b[B", b"\x1bOB"):
            return "DOWN"
        if raw in (b"\x1b[C", b"\x1bOC"):
            return "RIGHT"
        if raw in (b"\x1b[D", b"\x1bOD"):
            return "LEFT"
        if raw in (b"\x7f", b"\x08"):
            return "BACKSPACE"
        if raw.startswith(b"\x1b["):
            code = raw[2:]
            if code in (b"H", b"1~"):
                return "HOME"
            if code in (b"F", b"4~"):
                return "END"
            if code == b"5~":
                return "PAGEUP"
            if code == b"6~":
                return "PAGEDOWN"
            return "ESC"
        if raw in (b"\r", b"\n"):
            return "ENTER"
        if raw == b" ":
            return "SPACE"
        if raw in (b"\x03", b"\x04"):
            return "EXIT"
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)


def clear_screen() -> None:
    if sys.stdin.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def write_cleared(text: str) -> None:
    if not text:
        return
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if i == len(lines) - 1:
            sys.stdout.write(l)
        else:
            sys.stdout.write(f"{l}\033[K\n")


def show_logo(env: Optional[Environment] = None) -> None:
    if env is None:
        env = get_env()
    cols, lines = _get_terminal_size()
    if cols < 66 or lines < 20:
        mode_line = truncate_display(f"Mode: {env.mode_label} ({env.repo_dir})", max(12, cols - 4))
        logo = (
            f"{Colors.BOLD_PURPLE}\n  NYX NIRI{Colors.RESET}  "
            f"{Colors.BOLD_WHITE}{env.version}{Colors.RESET}\n"
            f"  {Colors.DARK_GRAY}{mode_line}{Colors.RESET}\n\n"
        )
        write_cleared(logo)
        return
    mode_line = truncate_display(
        f"Mode: {env.mode_label} ({env.repo_dir})",
        max(12, cols - 4),
    )
    logo = (
        f"{Colors.BOLD_PURPLE}\n"
        " ███╗   ██╗██╗   ██╗██╗  ██╗    ███╗   ██╗██╗██████╗ ██╗\n"
        " ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ████╗  ██║██║██╔══██╗██║\n"
        " ██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██╔██╗ ██║██║██████╔╝██║\n"
        " ██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║╚██╗██║██║██╔══██╗██║\n"
        " ██║ ╚████║   ██║   ██╔╝ ██╗    ██║ ╚████║██║██║  ██║██║\n"
        " ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝\n"
        f"{Colors.RESET}\n"
        f"  {Colors.BOLD_CYAN}Noctalia V5 & Niri Desktop Environment Setup{Colors.RESET} {Colors.DARK_GRAY}|{Colors.RESET} {Colors.BOLD_WHITE}{env.version}{Colors.RESET}\n"
        f"  {Colors.DARK_GRAY}{mode_line}{Colors.RESET}\n\n"
    )
    write_cleared(logo)


def render_breadcrumb(trail: Optional[List[str]]) -> None:
    if not trail:
        return
    sep = f" {Colors.DARK_GRAY}›{Colors.RESET} "
    write_cleared(f"  {sep.join(trail)}\n\n")


def render_menu_item(idx: int, label: str, focus: int, style: str = "normal") -> None:
    if idx == focus:
        prefix = f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}"
        if style == "warn":
            color = Colors.BOLD_RED
        elif style == "subtle":
            color = Colors.DARK_GRAY
        else:
            color = Colors.BOLD_WHITE
    else:
        prefix = "    "
        if style == "warn":
            color = Colors.RED
        elif style == "subtle":
            color = Colors.DARK_GRAY
        else:
            color = ""
    cols, _ = _get_terminal_size()
    avail = max(1, cols - display_width(prefix) - 1)
    clipped = truncate_display(label, avail)
    sys.stdout.write(f"{prefix}{color}{clipped}{Colors.RESET}\033[K\n")


def render_check_row(is_focus: bool, chk: str, label: str) -> None:
    prefix = f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}" if is_focus else "    "
    cols, _ = _get_terminal_size()
    avail = max(1, cols - display_width(prefix) - display_width(chk) - 2)
    clipped = truncate_display(label, avail)
    if is_focus:
        sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}{chk} {Colors.BOLD_WHITE}{clipped}{Colors.RESET}\033[K\n")
    else:
        sys.stdout.write(f"    {chk} {clipped}\033[K\n")


def press_any_key() -> None:
    if sys.stdin.isatty():
        sys.stdout.write(msg("press_any_key"))
        sys.stdout.flush()
        read_key()
        sys.stdout.write("\n")


def prompt_confirm(key: str, default: str = "y") -> bool:
    if os.environ.get("NYXNIRI_AUTO_YES", "0") == "1":
        return True
    sys.stdout.write(msg(key))
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
        if not line:
            return default.lower().startswith("y")
        line = line.strip()
        if not line:
            return default.lower().startswith("y")
        return line.lower().startswith("y")
    except Exception:
        return default.lower().startswith("y")

class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, label: str):
        self.label = label
        self._stop = False
        self._thread = None

    def __enter__(self):
        self._stop = False
        def _spin():
            i = 0
            while not self._stop:
                sys.stdout.write(f"\r{Colors.BOLD_CYAN}{self.FRAMES[i % len(self.FRAMES)]}{Colors.RESET} {self.label}")
                sys.stdout.flush()
                i += 1
                time.sleep(0.08)
        self._thread = threading.Thread(target=_spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


def read_line(prompt: str, default: str = "") -> str:
    if not sys.stdin.isatty():
        return default
    buf = list(default)
    cursor = len(default)
    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            sys.stdout.write(f"\r\033[K{prompt}{''.join(buf)}")
            sys.stdout.write(f"\r{' ' * cursor}")
            sys.stdout.flush()
            key = read_key()
            if key == "ENTER":
                sys.stdout.write("\n")
                return "".join(buf)
            if key == "ESC":
                sys.stdout.write("\n")
                return default
            if key == "BACKSPACE":
                if cursor > 0:
                    buf.pop(cursor - 1)
                    cursor -= 1
            elif key == "LEFT":
                if cursor > 0:
                    cursor -= 1
            elif key == "RIGHT":
                if cursor < len(buf):
                    cursor += 1
            elif key == "HOME":
                cursor = 0
            elif key == "END":
                cursor = len(buf)
            elif key == "EXIT":
                raise KeyboardInterrupt
            elif len(key) == 1 and key.isprintable():
                buf.insert(cursor, key)
                cursor += 1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
        sys.stdout.flush()

@dataclass
class MenuItem:
    label: str
    action: Any = None
    style: str = "normal"
    group_header: Optional[str] = None

class Menu:
    def __init__(self, title_key: str, items: List[MenuItem], hint_key: str = "menu_hint",
                 breadcrumb: Optional[List[str]] = None):
        self.title_key = title_key
        self.items = items
        self.hint_key = hint_key
        self.breadcrumb = breadcrumb

    def run(self, initial_focus: int = 0) -> int:
        if not sys.stdin.isatty():
            return len(self.items) - 1
        clear_screen()
        focus = initial_focus
        max_idx = len(self.items) - 1
        env = get_env()
        redraw = True
        def _set_redraw():
            nonlocal redraw
            redraw = True
        _register_winch(_set_redraw)
        sys.stdout.write(Colors.CURSOR_HIDE)
        try:
            while True:
                if redraw:
                    sys.stdout.write("\033[?25l\033[H")
                    show_logo(env)
                    if self.breadcrumb:
                        render_breadcrumb(self.breadcrumb)
                    title = msg(self.title_key).strip("\n")
                    write_cleared(f"{title}\n\n")
                    cols, term_lines = _get_terminal_size()
                    visible = max(3, term_lines - 18)
                    start = max(0, min(focus - visible // 2, len(self.items) - visible))
                    end = min(len(self.items), start + visible)
                    if start > 0:
                        write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    for i in range(start, end):
                        item = self.items[i]
                        if item.group_header:
                            hdr = truncate_display(item.group_header, max(1, cols - 1))
                            write_cleared(f"{hdr}\n")
                        render_menu_item(i, item.label, focus, item.style)
                    if end < len(self.items):
                        write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    hint = responsive_hint(self.hint_key).strip("\n")
                    write_cleared(f"\n{hint}\n")
                    sys.stdout.write("\033[J")
                    sys.stdout.flush()
                    redraw = False
                key = read_key()
                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus = max_idx if focus <= 0 else focus - 1
                    redraw = True
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus = 0 if focus >= max_idx else focus + 1
                    redraw = True
                elif key in ("ENTER", "SPACE"):
                    return focus
                elif key.isdigit() and 1 <= int(key) <= len(self.items):
                    return int(key) - 1
                elif key in ("0", "q", "Q"):
                    return max_idx
                elif key in ("ESC", "EXIT"):
                    return max_idx
        finally:
            _unregister_winch(_set_redraw)
            sys.stdout.write(Colors.CURSOR_SHOW)
            sys.stdout.flush()

@dataclass
class CheckboxEntry:
    key: str
    label: str
    checked: bool = False
    is_separator: bool = False

class CheckboxList:
    def __init__(self, title_key: str, entries: List[CheckboxEntry], hint_key: str = "selective_hint",
                 breadcrumb: Optional[List[str]] = None):
        self.title_key = title_key
        self.entries = entries
        self.hint_key = hint_key
        self.breadcrumb = breadcrumb

    def run(self, accept_defaults: bool = False) -> Optional[List[str]]:
        if not any(not e.is_separator for e in self.entries):
            return []
        if not sys.stdin.isatty():
            return [e.key for e in self.entries if not e.is_separator and e.checked] if accept_defaults else None
        clear_screen()
        selectable = [i for i, e in enumerate(self.entries) if not e.is_separator]
        focus = 0
        env = get_env()
        redraw = True
        def _set_redraw():
            nonlocal redraw
            redraw = True
        _register_winch(_set_redraw)
        sys.stdout.write(Colors.CURSOR_HIDE)
        try:
            while True:
                if redraw:
                    sys.stdout.write("\033[?25l\033[H")
                    show_logo(env)
                    if self.breadcrumb:
                        render_breadcrumb(self.breadcrumb)
                    title = msg(self.title_key).strip("\n")
                    write_cleared(f"{title}\n\n")
                    focus_idx = selectable[focus]
                    cols, term_lines = _get_terminal_size()
                    visible = max(4, term_lines - 18)
                    start = max(0, min(focus_idx - visible // 2, len(self.entries) - visible))
                    end = min(len(self.entries), start + visible)
                    if start > 0:
                        write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    for i in range(start, end):
                        e = self.entries[i]
                        if e.is_separator:
                            write_cleared(f"{e.label}\n")
                            continue
                        chk = f"{Colors.BOLD_GREEN}[✓]{Colors.RESET}" if e.checked else f"{Colors.DARK_GRAY}[ ]{Colors.RESET}"
                        render_check_row(i == focus_idx, chk, e.label)
                    if end < len(self.entries):
                        write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    hint = responsive_hint(self.hint_key).strip("\n")
                    write_cleared(f"\n{hint}\n")
                    sys.stdout.write("\033[J")
                    sys.stdout.flush()
                    redraw = False
                key = read_key()
                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus = (focus - 1) % len(selectable)
                    redraw = True
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus = (focus + 1) % len(selectable)
                    redraw = True
                elif key == "SPACE":
                    idx = selectable[focus]
                    self.entries[idx].checked = not self.entries[idx].checked
                    redraw = True
                elif key in ("a", "A"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = True
                    redraw = True
                elif key in ("n", "N"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = False
                    redraw = True
                elif key in ("0", "q", "Q", "ESC", "EXIT"):
                    return None
                elif key.isdigit():
                    num = int(key) - 1
                    if 0 <= num < len(selectable):
                        focus = num
                        idx = selectable[focus]
                        self.entries[idx].checked = not self.entries[idx].checked
                        redraw = True
                elif key == "ENTER":
                    return [e.key for e in self.entries if not e.is_separator and e.checked]
        finally:
            _unregister_winch(_set_redraw)
            sys.stdout.write(Colors.CURSOR_SHOW)
            sys.stdout.flush()


def select_language() -> str:
    if not sys.stdin.isatty():
        from nyxniri.i18n import get_lang
        return get_lang()

    clear_screen()
    from nyxniri.i18n import set_lang
    env = get_env()
    focus = 1
    redraw = True
    def _set_redraw():
        nonlocal redraw
        redraw = True
    _register_winch(_set_redraw)
    sys.stdout.write(Colors.CURSOR_HIDE)
    try:
        while True:
            if redraw:
                sys.stdout.write("\033[?25l\033[H")
                show_logo(env)
                write_cleared(f"  {Colors.BOLD_CYAN}── 请选择语言 / Select Language ──{Colors.RESET}\n\n")
                if focus == 0:
                    sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}English{Colors.RESET}\033[K\n")
                    sys.stdout.write(f"    {Colors.DARK_GRAY}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")
                else:
                    sys.stdout.write(f"    {Colors.DARK_GRAY}English{Colors.RESET}\033[K\n")
                    sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")
                write_cleared(f"\n  {Colors.DARK_GRAY}[↑/↓] Move  [Enter] Select\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()
                redraw = False
            key = read_key()
            if key in ("UP", "k", "K", "LEFT", "h", "H", "1"):
                focus = 0
                redraw = True
            elif key in ("DOWN", "j", "J", "RIGHT", "l", "L", "2"):
                focus = 1
                redraw = True
            elif key in ("ENTER", "SPACE"):
                chosen = "en" if focus == 0 else "zh"
                set_lang(chosen)
                clear_screen()
                return chosen
            elif key in ("ESC", "EXIT"):
                sys.exit(130)
    finally:
        _unregister_winch(_set_redraw)
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()
