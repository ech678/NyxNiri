"""TUI component and terminal presentation engine (Native ANSI + Standard Library)."""

import atexit
import os
import re
import select
import shutil
import signal
import sys
import termios
import tty
import unicodedata
from dataclasses import dataclass
from typing import Any, List, Optional

from nyxniri.colors import Colors
from nyxniri.env import Environment, get_env
from nyxniri.i18n import msg

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class TerminalGuard:
    """Fail-safe guard that guarantees terminal attributes and cursor visibility are restored."""
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
    """Calculate the real physical terminal column width of a string (CJK = 2 cols)."""
    clean_text = ANSI_ESCAPE_RE.sub("", text)
    return sum(
        0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in clean_text
    )


def pad_display(text: str, width: int) -> str:
    """Pad string with trailing spaces to achieve exact visual column alignment."""
    curr = display_width(text)
    if curr < width:
        return text + (" " * (width - curr))
    return text


def truncate_display(text: str, width: int, suffix: str = "…") -> str:
    """Clip ANSI-styled text to a physical terminal width without splitting CJK glyphs."""
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
        char = text[pos]
        char_width = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if used + char_width > content_width:
            break
        output.append(char)
        used += char_width
        pos += 1
    reset = Colors.RESET if ANSI_ESCAPE_RE.search(text) else ""
    return "".join(output) + suffix + reset


def responsive_hint(key: str) -> str:
    """Use compact control hints when the terminal cannot hold the full legend."""
    if shutil.get_terminal_size((80, 24)).columns >= 72:
        return msg(key)
    short_keys = {
        "menu_hint": "menu_hint_short",
        "submenu_hint": "submenu_hint_short",
        "selective_hint": "checklist_hint_short",
        "delete_snapshot_hint": "checklist_hint_short",
        "dep_menu_hint": "checklist_hint_short",
        "opt_apps_menu_hint": "checklist_hint_short",
        "summary_action_hint": "summary_action_hint_short",
    }
    return msg(short_keys.get(key, key))


def read_key() -> str:
    """Listen for a single keyboard event using raw unbuffered OS file descriptor reads."""
    if not sys.stdin.isatty():
        return "ENTER"

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        raw_bytes = os.read(fd, 1)
        if not raw_bytes:
            return "EOF"
        if raw_bytes == b"\x1b":
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready:
                raw_bytes += os.read(fd, 31)

        if raw_bytes == b"\x1b":
            return "ESC"

        if raw_bytes in (b"\x1b[A", b"\x1bOA"):
            return "UP"
        if raw_bytes in (b"\x1b[B", b"\x1bOB"):
            return "DOWN"
        if raw_bytes in (b"\x1b[C", b"\x1bOC"):
            return "RIGHT"
        if raw_bytes in (b"\x1b[D", b"\x1bOD"):
            return "LEFT"

        if raw_bytes.startswith(b"\x1b["):
            code = raw_bytes[2:]
            if code in (b"H", b"1~"):
                return "HOME"
            if code in (b"F", b"4~"):
                return "END"
            if code == b"5~":
                return "PAGEUP"
            if code == b"6~":
                return "PAGEDOWN"
            return "ESC"

        if raw_bytes in (b"\r", b"\n"):
            return "ENTER"
        if raw_bytes == b" ":
            return "SPACE"
        if raw_bytes in (b"\x03", b"\x04"):
            return "EXIT"

        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)

def clear_screen() -> None:
    """Clear the visible terminal without destroying scrollback history."""
    if sys.stdin.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def write_cleared(text: str) -> None:
    """Write text, ensuring each line has \\033[K before \\n to wipe right-side ghost chars."""
    if not text:
        return
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            sys.stdout.write(line)
        else:
            sys.stdout.write(f"{line}\033[K\n")

def show_logo(env: Optional[Environment] = None) -> None:
    """Render the official NyxNiri ASCII brand header."""
    if env is None:
        env = get_env()

    terminal = shutil.get_terminal_size((80, 24))
    if terminal.columns < 66 or terminal.lines < 20:
        mode_line = truncate_display(f"Mode: {env.mode_label} ({env.repo_dir})", max(12, terminal.columns - 4))
        logo = (
            f"{Colors.BOLD_PURPLE}\n  NYX NIRI{Colors.RESET}  "
            f"{Colors.BOLD_WHITE}{env.version}{Colors.RESET}\n"
            f"  {Colors.DARK_GRAY}{mode_line}{Colors.RESET}\n\n"
        )
        write_cleared(logo)
        return

    mode_line = truncate_display(
        f"Mode: {env.mode_label} ({env.repo_dir})",
        max(12, terminal.columns - 4),
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

def render_menu_item(idx: int, label: str, focus: int, style: str = "normal") -> None:
    """Render a single interactive menu row with line-level erase."""
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
    available = max(1, shutil.get_terminal_size((80, 24)).columns - display_width(prefix) - 1)
    clipped_label = truncate_display(label, available)
    sys.stdout.write(f"{prefix}{color}{clipped_label}{Colors.RESET}\033[K\n")

def render_check_row(is_focus: bool, check_str: str, label: str) -> None:
    """Render a single checkbox item row with line-level erase."""
    prefix = f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}" if is_focus else "    "
    available = max(
        1,
        shutil.get_terminal_size((80, 24)).columns
        - display_width(prefix)
        - display_width(check_str)
        - 2,
    )
    clipped_label = truncate_display(label, available)
    if is_focus:
        sys.stdout.write(
            f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}{check_str} "
            f"{Colors.BOLD_WHITE}{clipped_label}{Colors.RESET}\033[K\n"
        )
    else:
        sys.stdout.write(f"    {check_str} {clipped_label}\033[K\n")

def press_any_key() -> None:
    """Prompt to press any key to continue."""
    if sys.stdin.isatty():
        sys.stdout.write(msg("press_any_key"))
        sys.stdout.flush()
        read_key()
        sys.stdout.write("\n")

def prompt_confirm(prompt_key: str, default: str = "y") -> bool:
    """Bilingual prompt confirmation (returns True for Yes, False for No)."""
    if os.environ.get("NYXNIRI_AUTO_YES", "0") == "1":
        return True

    sys.stdout.write(msg(prompt_key))
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

@dataclass
class MenuItem:
    label: str
    action: Any = None
    style: str = "normal"
    group_header: Optional[str] = None


class Menu:
    def __init__(self, title_key: str, items: List[MenuItem], hint_key: str = "menu_hint"):
        self.title_key = title_key
        self.items = items
        self.hint_key = hint_key

    def run(self, initial_focus: int = 0) -> int:
        """Run interactive menu loop and return the selected item index."""
        if not sys.stdin.isatty():
            return len(self.items) - 1

        clear_screen()
        focus = initial_focus
        max_idx = len(self.items) - 1
        env = get_env()

        sys.stdout.write(Colors.CURSOR_HIDE)
        try:
            while True:
                sys.stdout.write("\033[?25l\033[H")
                show_logo(env)
                title = msg(self.title_key).strip("\n")
                write_cleared(f"{title}\n\n")

                terminal_lines = shutil.get_terminal_size((80, 24)).lines
                visible_count = max(3, terminal_lines - 18)
                start = max(0, min(focus - visible_count // 2, len(self.items) - visible_count))
                end = min(len(self.items), start + visible_count)
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                for curr_idx in range(start, end):
                    item = self.items[curr_idx]
                    if item.group_header:
                        header = truncate_display(
                            item.group_header,
                            max(1, shutil.get_terminal_size((80, 24)).columns - 1),
                        )
                        write_cleared(f"{header}\n")
                    render_menu_item(curr_idx, item.label, focus, item.style)
                if end < len(self.items):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")

                hint = responsive_hint(self.hint_key).strip("\n")
                write_cleared(f"\n{hint}\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()
                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus = max_idx if focus <= 0 else focus - 1
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus = 0 if focus >= max_idx else focus + 1
                elif key in ("ENTER", "SPACE"):
                    return focus
                elif key.isdigit() and 1 <= int(key) <= len(self.items):
                    return int(key) - 1
                elif key in ("0", "q", "Q"):
                    return max_idx
                elif key in ("ESC", "EXIT"):
                    return max_idx
        finally:
            sys.stdout.write(Colors.CURSOR_SHOW)
            sys.stdout.flush()

@dataclass
class CheckboxEntry:
    key: str
    label: str
    checked: bool = False
    is_separator: bool = False


class CheckboxList:
    def __init__(self, title_key: str, entries: List[CheckboxEntry], hint_key: str = "selective_hint"):
        self.title_key = title_key
        self.entries = entries
        self.hint_key = hint_key

    def run(self, accept_defaults: bool = False) -> Optional[List[str]]:
        """Run checkbox selection loop. Returns list of selected keys, or None if cancelled."""
        if not any(not entry.is_separator for entry in self.entries):
            return []
        if not sys.stdin.isatty():
            if accept_defaults:
                return [e.key for e in self.entries if not e.is_separator and e.checked]
            return None

        clear_screen()
        selectable = [idx for idx, entry in enumerate(self.entries) if not entry.is_separator]
        focus_pos = 0

        env = get_env()
        sys.stdout.write(Colors.CURSOR_HIDE)
        try:
            while True:
                sys.stdout.write("\033[?25l\033[H")
                show_logo(env)
                title = msg(self.title_key).strip("\n")
                write_cleared(f"{title}\n\n")

                focus = selectable[focus_pos]
                terminal_lines = shutil.get_terminal_size((80, 24)).lines
                visible_count = max(4, terminal_lines - 18)
                start = max(
                    0,
                    min(focus - visible_count // 2, len(self.entries) - visible_count),
                )
                end = min(len(self.entries), start + visible_count)
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                for idx in range(start, end):
                    entry = self.entries[idx]
                    if entry.is_separator:
                        write_cleared(f"{entry.label}\n")
                        continue

                    check_str = (
                        f"{Colors.BOLD_GREEN}[✓]{Colors.RESET}"
                        if entry.checked
                        else f"{Colors.DARK_GRAY}[ ]{Colors.RESET}"
                    )
                    render_check_row(idx == focus, check_str, entry.label)
                if end < len(self.entries):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")

                hint = responsive_hint(self.hint_key).strip("\n")
                write_cleared(f"\n{hint}\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()
                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus_pos = (focus_pos - 1) % len(selectable)
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus_pos = (focus_pos + 1) % len(selectable)
                elif key == "SPACE":
                    self.entries[focus].checked = not self.entries[focus].checked
                elif key in ("a", "A"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = True
                elif key in ("n", "N"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = False
                elif key in ("0", "q", "Q", "ESC", "EXIT"):
                    return None
                elif key.isdigit():
                    num = int(key) - 1
                    if 0 <= num < len(selectable):
                        focus_pos = num
                        entry_idx = selectable[focus_pos]
                        self.entries[entry_idx].checked = not self.entries[entry_idx].checked
                elif key == "ENTER":
                    return [e.key for e in self.entries if not e.is_separator and e.checked]
        finally:
            sys.stdout.write(Colors.CURSOR_SHOW)
            sys.stdout.flush()

def select_language() -> str:
    """Prompt user to select language mode with smooth arrow keys."""
    if not sys.stdin.isatty():
        from nyxniri.i18n import get_lang
        return get_lang()

    clear_screen()
    from nyxniri.i18n import set_lang
    env = get_env()
    focus = 1

    sys.stdout.write(Colors.CURSOR_HIDE)
    try:
        while True:
            sys.stdout.write("\033[?25l\033[H")
            show_logo(env)
            write_cleared(f"  {Colors.BOLD_CYAN}── 请选择语言 / Select Language ──{Colors.RESET}\n\n")

            if focus == 0:
                sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}English{Colors.RESET}\033[K\n")
                sys.stdout.write(f"    {Colors.DARK_GRAY}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")
            else:
                sys.stdout.write(f"    {Colors.DARK_GRAY}English{Colors.RESET}\033[K\n")
                sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")

            hint = "[↑/↓] Move  [Enter] Select"
            write_cleared(f"\n  {Colors.DARK_GRAY}{hint}{Colors.RESET}\n")
            sys.stdout.write("\033[J")
            sys.stdout.flush()

            key = read_key()
            if key in ("UP", "k", "K", "LEFT", "h", "H", "1"):
                focus = 0
            elif key in ("DOWN", "j", "J", "RIGHT", "l", "L", "2"):
                focus = 1
            elif key in ("ENTER", "SPACE"):
                chosen = "en" if focus == 0 else "zh"
                set_lang(chosen)
                clear_screen()
                return chosen
            elif key in ("ESC", "EXIT"):
                sys.exit(130)
    finally:
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()
