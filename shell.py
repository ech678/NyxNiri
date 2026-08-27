import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, Pango
from gi.repository import GtkLayerShell as Layer
import subprocess
import os
import sys
import json
import time
import socket
import threading
import signal

_BAR_CSS = """
* {
    font-family: "JetBrains Mono", "Noto Sans CJK SC";
    font-size: 13px;
}
#bar {
    background-color: rgba(0, 0, 0, 0);
    padding: 0;
    margin: 0;
}
.capsule {
    background-color: rgba(VAR_SURFACE, 0.79);
    border-radius: 80px;
    padding: 4px 12px;
    margin: 0 2px;
}
.capsule-label {
    color: VAR_ON_SURFACE;
}
.capsule-button {
    color: VAR_ON_SURFACE;
    background: none;
    border: none;
    padding: 2px 8px;
    border-radius: 80px;
}
.capsule-button:hover {
    background-color: rgba(VAR_PRIMARY, 0.15);
}
#launcher-button {
    color: VAR_PRIMARY;
    font-weight: bold;
}
.clock-label {
    color: VAR_ON_SURFACE_VARIANT;
}
.session-button {
    color: VAR_ON_SURFACE;
    background: none;
    border: none;
    padding: 6px 16px;
    border-radius: 12px;
    font-size: 14px;
}
.session-button.destructive {
    color: VAR_ERROR;
}
.session-button:hover {
    background-color: rgba(VAR_PRIMARY, 0.12);
}
#osd {
    background-color: rgba(VAR_SURFACE, 0.85);
    border-radius: 12px;
    padding: 12px 24px;
}
#osd-label {
    color: VAR_ON_SURFACE;
}
.osd-bar {
    margin-top: 8px;
}
.osd-scale trough {
    background-color: rgba(VAR_OUTLINE, 0.3);
    border-radius: 4px;
    min-height: 6px;
}
.osd-scale highlight {
    background-color: VAR_PRIMARY;
    border-radius: 4px;
}
#popup {
    background-color: rgba(VAR_SURFACE, 0.92);
    border-radius: 16px;
    border: 1px solid rgba(VAR_OUTLINE, 0.15);
}
.popup-row {
    padding: 8px 16px;
    border-radius: 8px;
}
.popup-row:hover {
    background-color: rgba(VAR_PRIMARY, 0.1);
}
.popup-row.selected {
    background-color: rgba(VAR_PRIMARY, 0.15);
}
.popup-row-label {
    color: VAR_ON_SURFACE;
}
.popup-entry {
    margin: 8px;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid rgba(VAR_OUTLINE, 0.2);
    background-color: rgba(VAR_SURFACE_CONTAINER, 0.8);
    color: VAR_ON_SURFACE;
}
"""

_CONFIG_PATH = os.path.expanduser("~/.config/noctalia/noctalia-config.toml")
_SOCKET_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", f"/tmp/noctalia-{os.getuid()}"),
    "noctalia.sock",
)

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _load_config():
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get_css_colors():
    css_path = os.path.expanduser("~/.config/gtk-4.0/gtk.css")
    if not os.path.isfile(css_path):
        css_path = os.path.expanduser("~/.config/gtk-3.0/gtk.css")
    colors = {
        "VAR_SURFACE": "30, 29, 32",
        "VAR_ON_SURFACE": "228, 225, 233",
        "VAR_PRIMARY": "213, 183, 255",
        "VAR_ON_SURFACE_VARIANT": "202, 195, 207",
        "VAR_ERROR": "242, 184, 181",
        "VAR_OUTLINE": "121, 116, 126",
        "VAR_SURFACE_CONTAINER": "42, 41, 47",
    }
    if os.path.isfile(css_path):
        try:
            content = open(css_path, "r", errors="replace").read()
            for key in colors:
                import re
                name = key.replace("VAR_", "").lower()
                m = re.search(rf"@define-color\s+{name}\s+#([0-9a-fA-F]{{6}})", content)
                if m:
                    h = m.group(1)
                    r = int(h[0:2], 16)
                    g = int(h[2:4], 16)
                    b = int(h[4:6], 16)
                    colors[key] = f"{r}, {g}, {b}"
        except Exception:
            pass
    return colors


def _build_css():
    css = _BAR_CSS
    for k, v in _get_css_colors().items():
        css = css.replace(k, f"rgba({v}, 1)" if "VAR_" in k and "rgba(VAR_" not in css.split(k)[0][-10:] else f"rgba({v}, 1)")
    for k, v in _get_css_colors().items():
        css = css.replace(f"rgba({k}", f"rgba({v}")
    for k, v in _get_css_colors().items():
        css = css.replace(k, v)
    return css


def _ipc(msg):
    if not os.path.exists(_SOCKET_PATH):
        return "ERROR"
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(_SOCKET_PATH)
        s.sendall(msg.encode())
        resp = s.recv(4096).decode().strip()
        s.close()
        return resp
    except Exception:
        return "ERROR"


def _niri_msg(*args):
    try:
        r = subprocess.run(["niri", "msg", *args], capture_output=True, text=True, check=False, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _get_workspaces():
    out = _niri_msg("-j", "workspaces")
    if not out:
        return []
    try:
        return json.loads(out)
    except Exception:
        return []


def _get_active_window():
    out = _niri_msg("-j", "windows")
    if not out:
        return ""
    try:
        wins = json.loads(out)
        for w in wins:
            if w.get("is_focused"):
                return w.get("title", "")[:40]
    except Exception:
        pass
    return ""


def _get_volume():
    try:
        r = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, check=False, timeout=2)
        if r.returncode == 0:
            parts = r.stdout.strip().split()
            if len(parts) >= 2:
                vol = float(parts[1])
                muted = "[MUTED]" in r.stdout
                return vol, muted
    except Exception:
        pass
    return 0.0, True


def _get_media_title():
    try:
        r = subprocess.run(
            ["playerctl", "metadata", "--format", "{{title}} - {{artist}}"],
            capture_output=True, text=True, check=False, timeout=2
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:50]
    except Exception:
        pass
    return ""


class Bar(Gtk.Window):
    def __init__(self):
        super().__init__(title="noctalia-bar")
        self.set_name("bar")
        Layer.init_for_window(self)
        Layer.set_layer(self, Layer.Layer.TOP)
        Layer.set_anchor(self, Layer.Edge.TOP, True)
        Layer.set_anchor(self, Layer.Edge.LEFT, True)
        Layer.set_anchor(self, Layer.Edge.RIGHT, True)
        Layer.set_margin(self, Layer.Edge.TOP, 10)
        Layer.set_margin(self, Layer.Edge.LEFT, 14)
        Layer.set_margin(self, Layer.Edge.RIGHT, 14)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.connect("destroy", Gtk.main_quit)

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._box.set_homogeneous(False)
        self.add(self._box)

        self._start_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._end_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._start_box.get_style_context().add_class("capsule")
        self._center_box.get_style_context().add_class("capsule")
        self._end_box.get_style_context().add_class("capsule")

        self._build_start()
        self._build_center()
        self._build_end()

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(self._start_box, False, False, 0)
        outer.pack_start(Gtk.Label(), True, True, 0)
        outer.pack_start(self._center_box, False, False, 0)
        outer.pack_start(Gtk.Label(), True, True, 0)
        outer.pack_end(self._end_box, False, False, 0)
        self._box.pack_start(outer, True, True, 0)

        self.show_all()
        GLib.timeout_add(1000, self._tick)

    def _build_start(self):
        btn = Gtk.Button(label="◆")
        btn.set_name("launcher-button")
        btn.get_style_context().add_class("capsule-button")
        btn.connect("clicked", lambda *_: _toggle_panel("launcher"))
        self._start_box.pack_start(btn, False, False, 0)

        self._ws_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._start_box.pack_start(self._ws_box, False, False, 0)

        self._active_label = Gtk.Label()
        self._active_label.get_style_context().add_class("capsule-label")
        self._active_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._active_label.set_max_width_chars(30)
        self._start_box.pack_start(self._active_label, False, False, 4)

    def _build_center(self):
        self._clock_label = Gtk.Label()
        self._clock_label.get_style_context().add_class("clock-label")
        self._center_box.pack_start(self._clock_label, False, False, 0)

    def _build_end(self):
        self._media_label = Gtk.Label()
        self._media_label.get_style_context().add_class("capsule-label")
        self._media_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._media_label.set_max_width_chars(25)
        self._end_box.pack_start(self._media_label, False, False, 0)

        self._tray_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._end_box.pack_start(self._tray_box, False, False, 0)

        self._vol_btn = Gtk.Button(label="♪")
        self._vol_btn.get_style_context().add_class("capsule-button")
        self._vol_btn.connect("clicked", lambda *_: _toggle_volume_osd())
        self._end_box.pack_start(self._vol_btn, False, False, 0)

        self._notif_btn = Gtk.Button(label="▣")
        self._notif_btn.get_style_context().add_class("capsule-button")
        self._end_box.pack_start(self._notif_btn, False, False, 0)

        sess = Gtk.Button(label="⏻")
        sess.get_style_context().add_class("capsule-button")
        sess.connect("clicked", lambda *_: _toggle_panel("session"))
        self._end_box.pack_start(sess, False, False, 0)

    def _tick(self):
        self._clock_label.set_label(time.strftime("%a, %d %b %H:%M"))
        title = _get_active_window()
        if title:
            self._active_label.set_label(title)
        else:
            self._active_label.set_label("")
        media = _get_media_title()
        self._media_label.set_label(media)
        self._update_workspaces()
        return True

    def _update_workspaces(self):
        wss = _get_workspaces()
        if not wss:
            return
        active_idx = None
        for i, ws in enumerate(wss):
            if ws.get("is_focused") or ws.get("is_active"):
                active_idx = i
                break
        if active_idx is None and wss:
            active_idx = 0
        for child in self._ws_box.get_children():
            self._ws_box.remove(child)
        for i, ws in enumerate(wss):
            btn = Gtk.Button(label=str(ws.get("idx", i + 1)))
            btn.get_style_context().add_class("capsule-button")
            if i == active_idx:
                btn.get_style_context().add_class("selected")
            btn.connect("clicked", lambda _, idx=ws.get("idx", i+1): _niri_msg("action", "focus-workspace", str(idx)))
            self._ws_box.pack_start(btn, False, False, 0)
        self._ws_box.show_all()


class OSD(Gtk.Window):
    def __init__(self):
        super().__init__(title="noctalia-osd")
        self.set_name("osd")
        Layer.init_for_window(self)
        Layer.set_layer(self, Layer.Layer.OVERLAY)
        Layer.set_anchor(self, Layer.Edge.BOTTOM, True)
        Layer.set_margin(self, Layer.Edge.BOTTOM, 20)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.connect("destroy", lambda *_: self.hide())
        self._timeout_id = None
        self._label = Gtk.Label()
        self._label.set_name("osd-label")
        self._scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self._scale.set_range(0, 100)
        self._scale.set_sensitive(False)
        self._scale.get_style_context().add_class("osd-scale")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(self._label, False, False, 0)
        box.pack_start(self._scale, False, False, 0)
        box.set_spacing(8)
        self.add(box)

    def show_volume(self):
        vol, muted = _get_volume()
        self._label.set_text("Volume" + " (Muted)" if muted else "")
        self._scale.set_value(int(vol * 100))
        self.show_all()
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
        self._timeout_id = GLib.timeout_add(2000, lambda: (self.hide(), False)[1])


class Popup(Gtk.Window):
    def __init__(self, panel_type):
        super().__init__(title=f"noctalia-{panel_type}")
        self.set_name("popup")
        self._panel_type = panel_type
        Layer.init_for_window(self)
        Layer.set_layer(self, Layer.Layer.OVERLAY)
        if panel_type == "session":
            Layer.set_anchor(self, Layer.Edge.TOP, True)
            Layer.set_anchor(self, Layer.Edge.BOTTOM, True)
            Layer.set_anchor(self, Layer.Edge.LEFT, True)
            Layer.set_anchor(self, Layer.Edge.RIGHT, True)
        else:
            Layer.set_anchor(self, Layer.Edge.LEFT, True)
            Layer.set_anchor(self, Layer.Edge.RIGHT, True)
            Layer.set_margin(self, Layer.Edge.TOP, 50)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.connect("key-press-event", self._on_key)
        self.connect("focus-out-event", lambda *_: self.destroy())
        self._selected = 0
        self._items = []
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._entry = None
        self._build()
        self.show_all()
        self.grab_focus()

    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        if self._panel_type == "launcher":
            self._entry = Gtk.Entry()
            self._entry.set_placeholder_text("Search...")
            self._entry.get_style_context().add_class("popup-entry")
            self._entry.connect("changed", lambda *_: self._refresh())
            self._entry.connect("activate", self._activate_selected)
            box.pack_start(self._entry, False, False, 0)
        box.pack_start(self._list, False, False, 0)
        self.add(box)
        self._refresh()

    def _get_items(self):
        if self._panel_type == "launcher":
            return _get_apps()
        elif self._panel_type == "session":
            return [
                ("Lock", "lock", "default"),
                ("Log Out", "logout", "default"),
                ("Lock & Suspend", "lock_and_suspend", "default"),
                ("Reboot", "reboot", "default"),
                ("Shut Down", "shutdown", "destructive"),
            ]
        elif self._panel_type == "clipboard":
            return _get_clipboard()
        return []

    def _refresh(self):
        query = ""
        if self._entry:
            query = self._entry.get_text().lower()
        self._items = self._get_items()
        for child in self._list.get_children():
            self._list.remove(child)
        shown = 0
        for i, item in enumerate(self._items):
            label = item[0] if isinstance(item, tuple) else item
            if query and query not in label.lower():
                continue
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("popup-row")
            lbl = Gtk.Label(label=label)
            lbl.get_style_context().add_class("popup-row-label")
            if self._panel_type == "session" and len(item) > 2 and item[2] == "destructive":
                lbl.get_style_context().add_class("destructive")
            row.add(lbl)
            row.connect("activate", lambda r, idx=i: self._activate(idx))
            self._list.add(row)
            shown += 1
            if shown >= 12:
                break
        self._list.show_all()
        self._selected = 0
        if shown > 0:
            self._list.select_row(self._list.get_row_at_index(0))

    def _activate(self, idx):
        items = self._items
        if idx >= len(items):
            return
        item = items[idx]
        if self._panel_type == "launcher":
            app = item if isinstance(item, str) else item[0]
            _launch_app(app)
        elif self._panel_type == "session":
            action = item[1]
            _do_session_action(action)
        elif self._panel_type == "clipboard":
            _set_clipboard(item if isinstance(item, str) else item[0])
        self.destroy()

    def _activate_selected(self, *_):
        row = self._list.get_selected_row()
        if row:
            idx = row.get_index()
            self._activate(idx)

    def _on_key(self, _, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            self.destroy()
        elif key == "Up":
            self._move(-1)
        elif key == "Down":
            self._move(1)
        elif key == "Return":
            self._activate_selected()
        return True

    def _move(self, delta):
        total = len([c for c in self._list.get_children() if c.get_visible()])
        if total == 0:
            return
        self._selected = (self._selected + delta) % total
        self._list.select_row(self._list.get_row_at_index(self._selected))


_osd = None
_active_popup = None


def _toggle_volume_osd():
    global _osd
    if not _osd:
        _osd = OSD()
    _osd.show_volume()


def _toggle_panel(panel):
    global _active_popup
    if _active_popup:
        _active_popup.destroy()
        _active_popup = None
        if panel == _active_popup:
            return
    if panel == "settings":
        subprocess.Popen(["gnome-control-center"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    _active_popup = Popup(panel)


def _get_apps():
    apps = []
    for d in ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".desktop"):
                continue
            path = os.path.join(d, f)
            try:
                name = None
                exe = None
                no_display = False
                for line in open(path, errors="replace"):
                    line = line.strip()
                    if line.startswith("Name=") and not name:
                        name = line.split("=", 1)[1]
                    elif line.startswith("Exec=") and not exe:
                        exe = line.split("=", 1)[1].split()[0]
                    elif line.startswith("NoDisplay="):
                        no_display = "true" in line.lower()
                if name and exe and not no_display:
                    apps.append(name)
            except Exception:
                continue
    apps.sort()
    return apps


def _launch_app(name):
    subprocess.Popen(["sh", "-c", f"gtk-launch '{name}' || rofi -show drun"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _do_session_action(action):
    if action == "lock":
        subprocess.Popen(["swaylock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif action == "logout":
        subprocess.run(["niri", "msg", "action", "quit"], check=False)
    elif action == "lock_and_suspend":
        subprocess.Popen(["swaylock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "suspend"], check=False)
    elif action == "reboot":
        subprocess.run(["systemctl", "reboot"], check=False)
    elif action == "shutdown":
        subprocess.run(["systemctl", "poweroff"], check=False)


def _get_clipboard():
    try:
        r = subprocess.run(["wl-paste"], capture_output=True, text=True, check=False, timeout=2)
        if r.returncode == 0 and r.stdout:
            lines = r.stdout.strip().split("\n")
            return list(dict.fromkeys(lines))[:20]
    except Exception:
        pass
    return []


def _set_clipboard(text):
    try:
        subprocess.run(["wl-copy", text], check=False, timeout=2)
    except Exception:
        pass


def _watch_config():
    css_path = os.path.expanduser("~/.config/gtk-4.0/gtk.css")
    last_mtime = 0
    if os.path.isfile(css_path):
        last_mtime = os.path.getmtime(css_path)
    while True:
        time.sleep(2)
        try:
            if os.path.isfile(css_path):
                mtime = os.path.getmtime(css_path)
                if mtime != last_mtime:
                    last_mtime = mtime
                    GLib.idle_add(_reload_css)
        except Exception:
            pass


def _reload_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(_build_css().encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
    )


def main():
    Gtk.init(sys.argv)
    _reload_css()
    bar = Bar()
    t = threading.Thread(target=_watch_config, daemon=True)
    t.start()
    signal.signal(signal.SIGTERM, lambda *_: Gtk.main_quit())
    signal.signal(signal.SIGINT, lambda *_: Gtk.main_quit())
    Gtk.main()


if __name__ == "__main__":
    main()