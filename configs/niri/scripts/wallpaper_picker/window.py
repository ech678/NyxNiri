"""
NyxNiri Wallpaper Picker Main Window & Interaction Controller
GTK Widget-based Wayland Layer-Shell dialog with CSS styling.
"""

import sys
import os
import math
import random
import threading
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango, GdkPixbuf

from .palette import load_material_palette
from .lock import release_instance_lock
from .config import (
    WIN_WIDTH, WIN_HEIGHT, WIN_RADIUS,
    GRID_COLS, CARD_WIDTH, CARD_HEIGHT, THUMB_HEIGHT,
    GAP_X, GAP_Y, GRID_VIEWPORT_Y, GRID_VIEWPORT_H
)
from .scanner import WallpaperScanner
from .backend import apply_wallpaper, apply_random_wallpaper


_CSS_TEMPLATE = """
dialog-window {
    background: transparent;
}
.dialog {
    background: rgba({surf_r},{surf_g},{surf_b},0.96);
    border-radius: {radius}px;
    border: 1px solid rgba({out_r},{out_g},{out_b},0.20);
    box-shadow: 0 8px 32px rgba(0,0,0,0.28);
}
.header-title {
    color: rgba({on_r},{on_g},{on_b},0.98);
    font: 600 15px "Noto Sans CJK SC","Inter",sans-serif;
}
.search-pill {
    background: rgba({sb_r},{sb_g},{sb_b},0.50);
    border-radius: 18px;
    border: 1px solid rgba({out_r},{out_g},{out_b},0.25);
    color: rgba({onv_r},{onv_g},{onv_b},0.85);
    padding: 4px 12px;
    font: 10px "Noto Sans CJK SC",sans-serif;
    caret-color: rgba({pri_r},{pri_g},{pri_b},0.90);
}
.search-pill:focus {
    border-color: rgba({pri_r},{pri_g},{pri_b},0.85);
    border-width: 1.4px;
    outline: none;
}
.chip {
    background: rgba({sb_r},{sb_g},{sb_b},0.12);
    border-radius: 14px;
    border: 1px solid rgba({out_r},{out_g},{out_b},0.25);
    color: rgba({on_r},{on_g},{on_b},0.85);
    padding: 4px 12px;
    font: 500 9.5px "Noto Sans CJK SC","Inter",sans-serif;
    min-width: 52px;
}
.chip:checked {
    background: rgba({pri_r},{pri_g},{pri_b},0.95);
    color: rgba(25,26,29,0.98);
    border: none;
}
.chip:hover:not(:checked) {
    background: rgba({sb_r},{sb_g},{sb_b},0.25);
}
.card {
    background: rgba({sb_r},{sb_g},{sb_b},0.90);
    border-radius: 16px;
    border: 1px solid rgba({out_r},{out_g},{out_b},0.14);
    padding: 0;
    transition: border 200ms ease, box-shadow 200ms ease;
}
.card:hover {
    border: 2px solid rgba({pri_r},{pri_g},{pri_b},0.90);
    box-shadow: 0 4px 16px rgba({pri_r},{pri_g},{pri_b},0.25);
}
.card-current {
    border: 1.6px solid rgba({pri_r},{pri_g},{pri_b},0.60);
}
.card-title {
    color: rgba({on_r},{on_g},{on_b},0.95);
    font: 600 9.5px "Noto Sans CJK SC","Inter",sans-serif;
    padding: 4px 8px;
}
.card-live-tag {
    color: rgba({ter_r},{ter_g},{ter_b},1.0);
    font-weight: bold;
}
flowboxchild {
    padding: 0;
    border: none;
    background: transparent;
}
flowboxchild:selected {
    background: transparent;
}
scrollbar slider {
    background: rgba({pri_r},{pri_g},{pri_b},0.45);
    border-radius: 2px;
    min-width: 3.5px;
    min-height: 28px;
}
scrollbar trough {
    background: rgba({out_r},{out_g},{out_b},0.08);
    border-radius: 2px;
}
.scrolled-window {
    background: transparent;
}
"""


def _fi(rgb):
    return tuple(int(c * 255) for c in rgb)


class WallpaperPickerWindow(Gtk.Window):

    def __init__(self, lock_fd: int = None, pid_path: str = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("dialog-window")

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.palette = load_material_palette()

        self.scanner = WallpaperScanner(on_thumb_ready_cb=self._on_thumb_ready)
        self.scanner.scan()
        self.current_wp_path = self.scanner.get_current_wallpaper()

        self.active_cat_idx = 0
        self.search_query = ""
        self.is_dismissing = False
        self._entry_anim_id = None
        self._entry_opacity = 0.0

        self.chip_buttons = []
        self.card_widgets = {}
        self.search_entry = None
        self.flowbox = None
        self.scrolled_window = None

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self._load_css()
        self._build_ui()

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.STRUCTURE_MASK
        )
        self.connect("button-press-event", self._on_button_press)
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", lambda w, e: (self.dismiss_window(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.open_window()
        self.scanner.load_thumbnails_async()

    def _load_css(self):
        p = self.palette
        s = _fi
        css = _CSS_TEMPLATE.format(
            surf_r=s(p["surface"])[0], surf_g=s(p["surface"])[1], surf_b=s(p["surface"])[2],
            out_r=s(p["outline"])[0], out_g=s(p["outline"])[1], out_b=s(p["outline"])[2],
            on_r=s(p["on_surface"])[0], on_g=s(p["on_surface"])[1], on_b=s(p["on_surface"])[2],
            onv_r=s(p["on_surface_var"])[0], onv_g=s(p["on_surface_var"])[1], onv_b=s(p["on_surface_var"])[2],
            pri_r=s(p["primary"])[0], pri_g=s(p["primary"])[1], pri_b=s(p["primary"])[2],
            sb_r=s(p.get("surface_bright", (0.18, 0.20, 0.26)))[0],
            sb_g=s(p.get("surface_bright", (0.18, 0.20, 0.26)))[1],
            sb_b=s(p.get("surface_bright", (0.18, 0.20, 0.26)))[2],
            ter_r=s(p["tertiary"])[0], ter_g=s(p["tertiary"])[1], ter_b=s(p["tertiary"])[2],
            radius=int(WIN_RADIUS),
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.get_style_context().add_class("dialog")
        outer.set_size_request(int(WIN_WIDTH), int(WIN_HEIGHT))
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_start(32)
        main_box.set_margin_end(32)
        main_box.set_margin_top(22)
        main_box.set_margin_bottom(22)
        outer.pack_start(main_box, True, True, 0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        title_text = f"Wallpapers  ·  {len(self.scanner.items)}"
        title_label = Gtk.Label(label=title_text)
        title_label.get_style_context().add_class("header-title")
        title_label.set_halign(Gtk.Align.START)
        header.pack_start(title_label, True, True, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.get_style_context().add_class("search-pill")
        self.search_entry.set_size_request(260, 36)
        self.search_entry.set_placeholder_text("Search wallpapers...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_clear)
        header.pack_end(self.search_entry, False, False, 0)
        main_box.pack_start(header, False, False, 0)

        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cat_box.set_margin_top(14)
        for idx, cat_name in enumerate(self.scanner.categories):
            btn = Gtk.ToggleButton(label=cat_name)
            btn.get_style_context().add_class("chip")
            if idx == 0:
                btn.set_active(True)
            btn.connect("toggled", self._on_category_toggled, idx)
            cat_box.pack_start(btn, False, False, 0)
            self.chip_buttons.append(btn)
        main_box.pack_start(cat_box, False, False, 0)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.get_style_context().add_class("scrolled-window")
        self.scrolled_window.set_margin_top(14)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_width(True)
        self.scrolled_window.set_propagate_natural_height(True)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_min_children_per_line(GRID_COLS)
        self.flowbox.set_max_children_per_line(GRID_COLS)
        self.flowbox.set_column_spacing(int(GAP_X))
        self.flowbox.set_row_spacing(int(GAP_Y))
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.connect("child-activated", self._on_card_activated)
        self.scrolled_window.add(self.flowbox)
        main_box.pack_start(self.scrolled_window, True, True, 0)

        self.add(outer)
        self._populate_cards()

    def _populate_cards(self):
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)
        self.card_widgets = {}

        items = self._get_filtered_items()
        for idx, item in enumerate(items):
            card = self._create_card(item)
            self.flowbox.add(card)
            self.card_widgets[item.path] = card

        self.flowbox.show_all()

    def _create_card(self, item):
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_box.get_style_context().add_class("card")
        if item.path == self.current_wp_path:
            card_box.get_style_context().add_class("card-current")
        card_box.set_size_request(int(CARD_WIDTH), int(CARD_HEIGHT))

        img = Gtk.Image()
        img.set_size_request(int(CARD_WIDTH), int(THUMB_HEIGHT))
        if item.pixbuf:
            img.set_from_pixbuf(item.pixbuf)
        card_box.pack_start(img, False, False, 0)

        if item.is_video:
            title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            tag = Gtk.Label(label="[Live]")
            tag.get_style_context().add_class("card-live-tag")
            tag.set_valign(Gtk.Align.START)
            title_box.pack_start(tag, False, False, 0)
            title_lbl = Gtk.Label(label=item.title)
            title_lbl.get_style_context().add_class("card-title")
            title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            title_lbl.set_max_width_chars(28)
            title_lbl.set_xalign(0.0)
            title_box.pack_start(title_lbl, True, True, 0)
            card_box.pack_start(title_box, False, False, 0)
        else:
            title_lbl = Gtk.Label(label=item.title)
            title_lbl.get_style_context().add_class("card-title")
            title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            title_lbl.set_max_width_chars(32)
            title_lbl.set_xalign(0.0)
            card_box.pack_start(title_lbl, False, False, 0)

        return card_box

    def _get_filtered_items(self):
        if self.search_query.strip():
            q = self.search_query.strip().lower()
            return [it for it in self.scanner.items if q in it.title.lower() or q in it.filename.lower()]
        if 0 <= self.active_cat_idx < len(self.scanner.categories):
            cat_name = self.scanner.categories[self.active_cat_idx]
            return self.scanner.category_items.get(cat_name, [])
        return self.scanner.items

    def _on_thumb_ready(self, item):
        if item.pixbuf and item.path in self.card_widgets:
            card = self.card_widgets[item.path]
            for child in card.get_children():
                if isinstance(child, Gtk.Image):
                    child.set_from_pixbuf(item.pixbuf)
                    break

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text()
        self._populate_cards()

    def _on_search_clear(self, entry):
        entry.set_text("")
        self.search_query = ""
        self._populate_cards()

    def _on_category_toggled(self, button, idx):
        if button.get_active():
            self.active_cat_idx = idx
            for i, btn in enumerate(self.chip_buttons):
                if i != idx:
                    btn.set_active(False)
            self._populate_cards()

    def _on_card_activated(self, flowbox, child):
        if self.is_dismissing:
            return
        card = child.get_child()
        for path, widget in self.card_widgets.items():
            if widget == card:
                for item in self.scanner.items:
                    if item.path == path:
                        self.select_and_apply(item)
                        return

    def select_and_apply(self, item):
        self.dismiss_window()
        threading.Thread(target=apply_wallpaper, args=(item,), daemon=False).start()

    def _on_button_press(self, widget, event):
        if self.is_dismissing:
            return True
        if event.button in (2, 3):
            if self.search_query:
                self.search_entry.set_text("")
                self.search_query = ""
                self._populate_cards()
            else:
                self.dismiss_window()
            return True
        if event.button == 1:
            alloc = self.get_allocation()
            dw = min(WIN_WIDTH, alloc.width - 40)
            dh = min(WIN_HEIGHT, alloc.height - 40)
            dx = (alloc.width - dw) / 2.0
            dy = (alloc.height - dh) / 2.0
            if not (dx <= event.x <= dx + dw and dy <= event.y <= dy + dh):
                self.dismiss_window()
                return True
        return False

    def _on_key_press(self, widget, event):
        if self.is_dismissing:
            return True

        keyval = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)

        if keyval == Gdk.KEY_Escape:
            if self.search_query:
                self.search_entry.set_text("")
                self.search_query = ""
                self._populate_cards()
            else:
                self.dismiss_window()
            return True

        if ctrl:
            if keyval in (Gdk.KEY_r, Gdk.KEY_R):
                items = self._get_filtered_items()
                if items:
                    self.select_and_apply(random.choice(items))
                return True
            elif keyval in (Gdk.KEY_l, Gdk.KEY_L):
                self.search_entry.set_text("")
                self.search_query = ""
                self._populate_cards()
                self.search_entry.grab_focus()
                return True

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            items = self._get_filtered_items()
            selected = self.flowbox.get_selected_children()
            if selected:
                idx = selected[0].get_index()
                if idx < len(items):
                    self.select_and_apply(items[idx])
            elif items:
                self.select_and_apply(items[0])
            return True

        if keyval == Gdk.KEY_Down:
            children = self.flowbox.get_children()
            if children:
                selected = self.flowbox.get_selected_children()
                if selected:
                    cur = children.index(selected[0])
                    nxt = min(cur + GRID_COLS, len(children) - 1)
                    self.flowbox.select_child(children[nxt])
                    child = children[nxt]
                    adj = self.scrolled_window.get_vadjustment()
                    alloc = child.get_allocation()
                    if alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
                        adj.set_value(alloc.y + alloc.height - adj.get_page_size())
                else:
                    self.flowbox.select_child(children[0])
            return True

        if keyval == Gdk.KEY_Up:
            children = self.flowbox.get_children()
            if children:
                selected = self.flowbox.get_selected_children()
                if selected:
                    cur = children.index(selected[0])
                    nxt = max(cur - GRID_COLS, 0)
                    self.flowbox.select_child(children[nxt])
                    child = children[nxt]
                    adj = self.scrolled_window.get_vadjustment()
                    alloc = child.get_allocation()
                    if alloc.y < adj.get_value():
                        adj.set_value(alloc.y)
                else:
                    self.flowbox.select_child(children[0])
            return True

        if keyval == Gdk.KEY_Left:
            children = self.flowbox.get_children()
            if children:
                selected = self.flowbox.get_selected_children()
                if selected:
                    cur = children.index(selected[0])
                    if cur > 0:
                        self.flowbox.select_child(children[cur - 1])
                else:
                    self.flowbox.select_child(children[0])
            return True

        if keyval == Gdk.KEY_Right:
            children = self.flowbox.get_children()
            if children:
                selected = self.flowbox.get_selected_children()
                if selected:
                    cur = children.index(selected[0])
                    if cur < len(children) - 1:
                        self.flowbox.select_child(children[cur + 1])
                else:
                    self.flowbox.select_child(children[0])
            return True

        if keyval == Gdk.KEY_Home:
            children = self.flowbox.get_children()
            if children:
                self.flowbox.select_child(children[0])
                self.scrolled_window.get_vadjustment().set_value(0)
            return True

        if keyval == Gdk.KEY_End:
            children = self.flowbox.get_children()
            if children:
                self.flowbox.select_child(children[-1])
                child = children[-1]
                adj = self.scrolled_window.get_vadjustment()
                alloc = child.get_allocation()
                adj.set_value(alloc.y + alloc.height - adj.get_page_size())
            return True

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            step = -1 if (bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab) else 1
            self.active_cat_idx = (self.active_cat_idx + step) % len(self.scanner.categories)
            for i, btn in enumerate(self.chip_buttons):
                btn.set_active(i == self.active_cat_idx)
            return True

        if 32 <= keyval <= 126 and not ctrl:
            self.search_entry.grab_focus()
            return False

        return False

    def open_window(self):
        self.palette = load_material_palette()
        self.is_dismissing = False
        self._entry_opacity = 0.0
        self.set_opacity(0.0)
        self.show_all()
        self.present()
        self.search_entry.grab_focus()
        self._animate_entry_in()

    def _animate_entry_in(self):
        self._entry_opacity = min(1.0, self._entry_opacity + 0.08)
        t = self._entry_opacity
        alpha = t * t * (3.0 - 2.0 * t)
        self.set_opacity(alpha)
        if self._entry_opacity < 1.0:
            self._entry_anim_id = GLib.timeout_add(16, self._animate_entry_in)
        else:
            self._entry_anim_id = None

    def dismiss_window(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        if self._entry_anim_id is not None:
            GLib.source_remove(self._entry_anim_id)
            self._entry_anim_id = None
        self._animate_entry_out()

    def _animate_entry_out(self):
        self._entry_opacity = max(0.0, self._entry_opacity - 0.12)
        t = self._entry_opacity
        alpha = t * t * (3.0 - 2.0 * t)
        self.set_opacity(alpha)
        if self._entry_opacity > 0.01:
            self._entry_anim_id = GLib.timeout_add(16, self._animate_entry_out)
        else:
            self._finish_dismiss()

    def _finish_dismiss(self):
        self.scanner.shutdown()
        release_instance_lock(self.lock_fd, self.pid_path)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()