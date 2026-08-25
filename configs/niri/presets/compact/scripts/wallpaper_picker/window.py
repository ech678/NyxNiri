"""
NyxNiri Wallpaper Picker — Material You native widget edition.

A Wayland Layer-Shell dialog built from Gtk.FlowBox / Gtk.SearchEntry / M3 CSS,
replacing the Cairo hand-draw pipeline. Thumbnails are loaded on-demand via
CSS background-image, so off-screen cards hold no pixbufs in memory and
scrolling past a card releases its decoded image automatically.

The dynamic Material You palette is read from Noctalia's starship cache
(.cache/noctalia/starship-palette.toml) and injected into a CSS provider
at build time, so the whole dialog follows the wallpaper-derived tonal scheme.
"""

import os
import sys
import random
import threading
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

from .palette import load_material_palette
from .lock import release_instance_lock
from .config import (
    WIN_WIDTH, WIN_HEIGHT, WIN_RADIUS,
    GRID_COLS, CARD_WIDTH, THUMB_HEIGHT,
    GAP_X, GAP_Y,
)
from .scanner import WallpaperScanner
from .backend import apply_wallpaper


# ── M3 color helpers ────────────────────────────────────────────────────────
def _rgb(rgb):
    r, g, b = rgb
    return f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"


def _rgba(rgb, a):
    r, g, b = rgb
    return f"rgba({int(r * 255)},{int(g * 255)},{int(b * 255)},{a})"


def _on_primary(primary_rgb):
    """Pick black or white text on a primary fill via relative luminance (WCAG)."""
    pr, pg, pb = primary_rgb
    lum = 0.299 * pr + 0.587 * pg + 0.114 * pb
    return "#0b0c10" if lum > 0.55 else "#f5f6f9"


def _build_m3_css(palette: dict) -> str:
    p = palette
    on_surface = p["on_surface"]
    on_surface_var = p["on_surface_var"]
    surface = p["surface"]
    surface_dim = p["surface_dim"]
    surface_bright = p.get("surface_bright", p["surface"])
    primary = p["primary"]
    tertiary = p["tertiary"]
    outline = p["outline"]
    is_dark = p.get("is_dark", True)
    on_primary = _on_primary(primary)

    R = int(WIN_RADIUS)
    CR = 16  # card corner radius (M3 medium shape)
    chip_bg_idle = _rgba(surface_bright, 0.12 if is_dark else 0.22)
    chip_bg_hover = _rgba(surface_bright, 0.25 if is_dark else 0.40)
    outline_idle = _rgba(outline, 0.25 if is_dark else 0.35)
    outline_hover = _rgba(outline, 0.40 if is_dark else 0.50)

    return f"""
    window.background {{
        background-color: transparent;
    }}

    /* ── M3 dialog (elevated, extra-large shape) ── */
    .picker-dialog {{
        background-color: {_rgb(surface)};
        border-radius: {R}px;
        border: 1px solid {_rgba(outline, 0.20)};
        box-shadow: 0 2px 8px rgba(0,0,0,0.18), 0 12px 36px rgba(0,0,0,0.10);
        padding: 24px 28px 20px 28px;
        transition: opacity 220ms cubic-bezier(0.2, 0.0, 0, 1);
    }}
    .picker-dialog.dismissing {{ opacity: 0; }}

    .header {{ spacing: 12px; }}
    .header-title {{
        color: {_rgb(on_surface)};
        font-family: "Inter","Noto Sans CJK SC",sans-serif;
        font-weight: 600;
        font-size: 15pt;
    }}
    .header-count {{
        color: {_rgba(on_surface_var, 0.75)};
        font-size: 11pt;
    }}

    /* ── M3 search bar (pill, surface-container-high) ── */
    .search {{
        background-color: {_rgba(surface_bright, 0.55 if is_dark else 0.85)};
        border-radius: 18px;
        border: 1px solid {outline_idle};
        padding: 6px 12px;
        color: {_rgb(on_surface)};
        font-size: 10pt;
        caret-color: {_rgb(primary)};
        box-shadow: none;
        transition: border-color 160ms ease;
    }}
    .search:focus {{
        border-color: {_rgba(primary, 0.85)};
    }}

    /* ── M3 filter chips ── */
    .chips {{ spacing: 8px; }}
    .chip {{
        background-color: {chip_bg_idle};
        border: 1px solid {outline_idle};
        border-radius: 14px;
        padding: 4px 14px;
        color: {_rgb(on_surface)};
        font-size: 9.5pt;
        font-weight: 500;
        min-height: 20px;
        transition: background-color 140ms ease, border-color 140ms ease;
    }}
    .chip:hover {{
        background-color: {chip_bg_hover};
        border-color: {outline_hover};
    }}
    .chip:checked {{
        background-color: {_rgb(primary)};
        border-color: {_rgb(primary)};
        color: {on_primary};
    }}

    /* ── Card grid ── */
    .grid {{ background-color: transparent; }}
    .grid row {{ background-color: transparent; }}

    /* ── M3 card (filled, medium shape, state-layer on hover) ── */
    .card {{
        background-color: {_rgb(surface_bright)};
        border-radius: {CR}px;
        border: 1px solid {_rgba(outline, 0.14)};
        padding: 0;
        transition: background-color 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    }}
    .card:hover {{
        background-color: {_rgba(surface_bright, 0.92)};
        box-shadow: 0 4px 14px {_rgba(primary, 0.18)};
        border-color: {_rgba(primary, 0.45)};
    }}
    .card.current {{
        border-color: {_rgba(primary, 0.65)};
        border-width: 2px;
    }}
    .card-inner {{ background-color: transparent; spacing: 0; }}

    /* thumbnail: rounded top corners, image clipped to border-radius */
    .thumb {{
        background-color: {_rgb(surface_dim)};
        border-radius: {CR}px {CR}px 0 0;
        min-width: {int(CARD_WIDTH)}px;
        min-height: {int(THUMB_HEIGHT)}px;
    }}

    .info {{
        padding: 8px 12px;
        background-color: transparent;
    }}
    .card-title {{
        color: {_rgb(on_surface)};
        font-size: 9.5pt;
        font-weight: 600;
    }}
    .live {{
        color: {_rgb(tertiary)};
        font-weight: 700;
        font-size: 9.5pt;
        margin-right: 4px;
    }}

    /* ── M3 scrollbar ── */
    .grid-scroll {{ background-color: transparent; border: none; }}
    .grid-scroll scrollbar {{ background-color: transparent; }}
    .grid-scroll trough {{ background-color: {_rgba(outline, 0.08)}; border-radius: 2px; }}
    .grid-scroll scrollbar slider {{
        background-color: {_rgba(primary, 0.45)};
        border-radius: 2px;
        min-width: 3px;
        min-height: 28px;
    }}
    """


class WallpaperPickerWindow(Gtk.Window):
    """Material You wallpaper picker driven by native GTK widgets."""

    def __init__(self, lock_fd: int = None, pid_path: str = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("NyxNiriWallpaperPicker")

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.palette = load_material_palette()

        # View state — must be initialized BEFORE scanner.scan(), whose
        # pre-warm fires on_thumb_ready synchronously for cached thumbs.
        self.active_cat_idx = 0
        self.search_query = ""
        self.is_dismissing = False
        self._dismiss_timer = None
        self.thumb_widgets = {}      # hash_id -> thumb Gtk.Box
        self._applied_thumbs = set() # hash_ids that already got a CSS provider

        # Scanner and data
        self.scanner = WallpaperScanner(on_thumb_ready_cb=self.on_thumb_ready)
        self.scanner.scan()
        self.current_wp_path = self.scanner.get_current_wallpaper()

        # ── Wayland Layer-Shell overlay (unchanged from Cairo version) ──
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT,
                     GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # ── Material You CSS ──
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(_build_m3_css(self.palette).encode())
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"CSS load error: {e}", file=sys.stderr)

        self._build_ui()

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        self.connect("delete-event", lambda w, e: (self.dismiss_window(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.show_all()
        self.search_entry.grab_focus()
        self.scanner.load_thumbnails_async()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        dialog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        dialog.set_size_request(int(WIN_WIDTH), int(WIN_HEIGHT))
        dialog.get_style_context().add_class("picker-dialog")
        self.dialog = dialog

        # Header: title + count + search
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("header")
        title = Gtk.Label(label="Wallpapers")
        title.get_style_context().add_class("header-title")
        self.count_label = Gtk.Label(label=str(len(self.scanner.items)))
        self.count_label.get_style_context().add_class("header-count")
        header.pack_start(title, False, False, 0)
        header.pack_start(self.count_label, False, False, 0)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.pack_start(spacer, True, True, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search wallpapers...")
        self.search_entry.set_size_request(260, 36)
        self.search_entry.get_style_context().add_class("search")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("stop-search", self.on_stop_search)
        self.search_entry.connect("key-press-event", self.on_search_key_press)
        self.search_entry.connect("activate", self.on_search_activate)
        header.pack_end(self.search_entry, False, False, 0)

        dialog.pack_start(header, False, False, 0)

        # Category chips (M3 filter chips, single-active radio group)
        chips = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        chips.get_style_context().add_class("chips")
        self.chip_buttons = []
        for idx, cat in enumerate(self.scanner.categories):
            btn = Gtk.ToggleButton(label=cat)
            btn.get_style_context().add_class("chip")
            btn.set_active(idx == 0)
            btn.set_focus_on_click(False)
            btn.connect("toggled", self.on_chip_toggled, idx)
            chips.pack_start(btn, False, False, 0)
            self.chip_buttons.append(btn)
        dialog.pack_start(chips, False, False, 0)

        # Card grid (native FlowBox: lazy render + kinetic scroll + arrow nav)
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_min_children_per_line(GRID_COLS)
        self.flowbox.set_max_children_per_line(GRID_COLS)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(int(GAP_X))
        self.flowbox.set_row_spacing(int(GAP_Y))
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_activate_on_single_click(True)
        self.flowbox.get_style_context().add_class("grid")
        self.flowbox.connect("child-activated", self.on_child_activated)
        self.flowbox.connect("key-press-event", self.on_grid_key_press)

        scroll = Gtk.ScrolledWindow()
        scroll.get_style_context().add_class("grid-scroll")
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(494)
        scroll.add(self.flowbox)
        dialog.pack_start(scroll, True, True, 0)

        outer.add(dialog)
        self.add(outer)

        for item in self.scanner.items:
            self.flowbox.add(self._make_card(item))
        self.flowbox.set_filter_func(self._filter_func)
        self._refresh_count()

    def _make_card(self, item):
        child = Gtk.FlowBoxChild()
        child.get_style_context().add_class("card")
        if item.path == self.current_wp_path:
            child.get_style_context().add_class("current")
        child.item = item

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner.get_style_context().add_class("card-inner")

        thumb = Gtk.Box()
        thumb.get_style_context().add_class("thumb")
        inner.pack_start(thumb, False, False, 0)
        self.thumb_widgets[item.hash_id] = thumb
        # Thumbnail is applied later via on_thumb_ready (single path, dedup'd),
        # so cached and async-generated thumbs both flow through the same gate.

        info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        info.get_style_context().add_class("info")
        if item.is_video:
            live = Gtk.Label(label="[Live]")
            live.get_style_context().add_class("live")
            info.pack_start(live, False, False, 0)
        title_lbl = Gtk.Label(label=item.title)
        title_lbl.get_style_context().add_class("card-title")
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_max_width_chars(28)
        info.pack_start(title_lbl, False, False, 0)
        inner.pack_start(info, False, False, 0)

        child.add(inner)
        return child

    def _apply_thumb(self, thumb_box, thumb_path):
        """Render a thumbnail via CSS background-image (rounded-top, cover).

        Off-screen cards never decode this; GTK releases the decoded pixbuf
        when the widget leaves the viewport. This is the lazy-load/release
        memory model that the Cairo version lacked.
        """
        provider = Gtk.CssProvider()
        uri = "file://" + thumb_path.replace('"', "")
        css = (
            f'.thumb {{ background-image: url("{uri}");'
            f' background-size: cover; background-position: center; }}'
        )
        try:
            provider.load_from_data(css.encode())
            thumb_box.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
            )
        except Exception as e:
            print(f"thumb apply error: {e}", file=sys.stderr)

    # ── Filtering ────────────────────────────────────────────────────────────
    def _filter_func(self, child):
        item = child.item
        q = self.search_query.strip().lower()
        if q:
            return q in item.title.lower() or q in item.filename.lower()
        if self.active_cat_idx == 0:
            return True  # All
        cat = self.scanner.categories[self.active_cat_idx]
        if cat == "Static":
            return not item.is_video
        if cat == "Live":
            return item.is_video
        return item.category == cat

    def _visible_children(self):
        return [c for c in self.flowbox.get_children() if self._filter_func(c)]

    def _refresh_count(self):
        self.count_label.set_text(str(len(self._visible_children())))

    # ── Signal handlers ───────────────────────────────────────────────────────
    def on_search_changed(self, entry):
        self.search_query = entry.get_text()
        self.flowbox.invalidate_filter()
        self._refresh_count()

    def on_stop_search(self, entry):
        # SearchEntry emits stop-search on Esc-with-empty-text
        if not self.search_query:
            self.dismiss_window()

    def on_search_key_press(self, entry, event):
        if event.keyval == Gdk.KEY_Down:
            children = self._visible_children()
            if children:
                self.flowbox.grab_focus()
                self.flowbox.select_child(children[0])
            return True
        return False

    def on_search_activate(self, entry):
        children = self._visible_children()
        if children:
            self.select_and_apply(children[0].item)

    def on_chip_toggled(self, btn, idx):
        if not btn.get_active():
            return
        # single-active radio group
        for i, b in enumerate(self.chip_buttons):
            if i != idx and b.get_active():
                b.handler_block_by_func(self.on_chip_toggled)
                b.set_active(False)
                b.handler_unblock_by_func(self.on_chip_toggled)
        self.active_cat_idx = idx
        self.flowbox.invalidate_filter()
        self._refresh_count()
        self.search_entry.grab_focus()

    def on_child_activated(self, box, child):
        self.select_and_apply(child.item)

    def on_grid_key_press(self, box, event):
        # Up at the top row → hand focus back to the search bar
        if event.keyval == Gdk.KEY_Up:
            sel = self.flowbox.get_selected_children()
            visible = self._visible_children()
            if visible and (not sel or sel[0] == visible[0]):
                self.search_entry.grab_focus()
                return True
        return False

    def on_button_press(self, widget, event):
        if self.is_dismissing:
            return True
        # Right / middle click → clear search, or dismiss if already empty
        if event.button in (2, 3):
            if self.search_query:
                self.search_entry.set_text("")
            else:
                self.dismiss_window()
            return True
        # Left click outside the dialog → dismiss
        if event.button == 1 and self._click_outside_dialog(event.x, event.y):
            self.dismiss_window()
            return True
        return False

    def _click_outside_dialog(self, x, y):
        wa = self.get_allocation()
        da = self.dialog.get_allocation()
        if da.width == 0 or da.height == 0 or wa.width == 0:
            return False
        # dialog is centered in the (fullscreen) window
        dx = (wa.width - da.width) // 2
        dy = (wa.height - da.height) // 2
        return not (dx <= x <= dx + da.width and dy <= y <= dy + da.height)

    def on_key_press(self, widget, event):
        if self.is_dismissing:
            return True
        keyval = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)

        # Ctrl+R → apply a random wallpaper from the visible set
        if ctrl and keyval in (Gdk.KEY_r, Gdk.KEY_R):
            self._apply_random()
            return True

        # Esc outside the search bar → clear search, or dismiss if already empty
        if keyval == Gdk.KEY_Escape:
            if self.search_query:
                self.search_entry.set_text("")
                self.search_entry.grab_focus()
            else:
                self.dismiss_window()
            return True

        return False

    # ── Apply ─────────────────────────────────────────────────────────────────
    def select_and_apply(self, item):
        self.dismiss_window()
        threading.Thread(target=apply_wallpaper, args=(item,), daemon=False).start()

    def _apply_random(self):
        items = [c.item for c in self._visible_children()]
        if items:
            self.select_and_apply(random.choice(items))

    # ── Thumbnail callback ────────────────────────────────────────────────────
    def on_thumb_ready(self, item):
        """Scanner fired: apply the freshly-generated thumb file to its card.

        Called from multiple paths (pre-warm sync, pre-warm idle, load_thumbnails
        async, worker idle), so dedup on _applied_thumbs to avoid stacking
        CssProviders on the same style context.
        """
        if item.hash_id in self._applied_thumbs:
            return
        thumb = self.thumb_widgets.get(item.hash_id)
        if thumb and os.path.isfile(item.thumb_path):
            self._applied_thumbs.add(item.hash_id)
            self._apply_thumb(thumb, item.thumb_path)

    # ── Dismiss (fade out + release lock + quit) ──────────────────────────────
    def dismiss_window(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        self.dialog.get_style_context().add_class("dismissing")
        self._dismiss_timer = GLib.timeout_add(240, self._finish_dismiss)

    def _finish_dismiss(self):
        if self._dismiss_timer is not None:
            GLib.source_remove(self._dismiss_timer)
            self._dismiss_timer = None
        release_instance_lock(self.lock_fd, self.pid_path)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()
        return GLib.SOURCE_REMOVE
