"""
NyxNiri Wallpaper Picker Main Window & Interaction Controller
Stateless, event-driven Wayland Layer-Shell dialog with continuous smooth scrolling, spring physics, and pure M3E design.
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
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

from .physics import Spring
from .palette import load_material_palette
from .lock import release_instance_lock
from .config import (
    WIN_WIDTH, WIN_HEIGHT, WIN_RADIUS,
    GRID_COLS, CARD_WIDTH, CARD_HEIGHT, THUMB_HEIGHT,
    GAP_X, GAP_Y, GRID_VIEWPORT_Y, GRID_VIEWPORT_H
)
from .scanner import WallpaperScanner
from .backend import apply_wallpaper, apply_random_wallpaper
from .renderer import (
    draw_dialog_container, draw_header,
    draw_category_chips, draw_card, draw_scrollbar
)


class WallpaperPickerWindow(Gtk.Window):
    """Main M3E GtkLayerShell Wallpaper Picker Window with Pro-Grade Search Input."""

    def __init__(self, lock_fd: int = None, pid_path: str = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.palette = load_material_palette()

        # Scanner and data
        self.scanner = WallpaperScanner(on_thumb_ready_cb=self.on_thumb_ready)
        self.scanner.scan()
        self.current_wp_path = self.scanner.get_current_wallpaper()

        # View & Search state
        self.active_cat_idx = 0
        self.hover_cat_idx = None
        self.hovered_card_idx = None
        self.keyboard_selected_idx = None
        self.search_query = ""
        self.cursor_idx = 0
        self.search_active = True
        self.cursor_time = 0.0
        self.is_dismissing = False
        self._suppress_hover = False
        self._cached_items = None
        self._cached_items_key = None

        self.chip_boxes = []
        self.card_boxes = []
        self.search_box = None
        self.clear_box = None

        # High-Fidelity Motion Springs Matrix
        self.target_scroll_y = 0.0
        self.scroll_spring = Spring(0.0, omega=26.0, zeta=0.92)
        self.entry_spring = Spring(0.0, omega=18.0, zeta=0.82)
        self.card_springs = {}

        # Native Wayland CJK IME Context (Fcitx5 / IBus)
        self.im_context = Gtk.IMMulticontext()
        self.im_context.set_use_preedit(True)
        self.im_context.connect("commit", self.on_im_commit)
        self.im_context.connect("preedit-changed", lambda ctx: self._request_frame())

        # FrameClock callback & cursor blink timer
        self.tick_callback_id = None
        self.cursor_timer_id = None
        self.last_frame_time = 0

        # Layer Shell Setup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)

        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.KEY_RELEASE_MASK
            | Gdk.EventMask.STRUCTURE_MASK
        )

        self.connect("realize", self.on_realize)
        self.connect("draw", self.on_draw)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-press-event", self.on_button_press)
        self.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key_press)
        self.connect("delete-event", lambda w, e: (self.dismiss_window(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.open_window()
        self.scanner.load_thumbnails_async()

    def on_realize(self, widget):
        gdk_window = self.get_window()
        if gdk_window:
            self.im_context.set_client_window(gdk_window)

    def on_thumb_ready(self, item):
        """Called when a background thumbnail is ready to trigger instant visual repaint."""
        self.queue_draw()
        self._request_frame()

    def _on_cursor_blink_timer(self):
        if self.is_dismissing:
            self.cursor_timer_id = None
            return GLib.SOURCE_REMOVE
        if self.search_active:
            self.cursor_time += 0.5
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def open_window(self):
        self.palette = load_material_palette()
        self.is_dismissing = False
        self._suppress_hover = False
        self.hovered_card_idx = None
        self.hover_cat_idx = None
        self.keyboard_selected_idx = None
        self.entry_spring.omega = 16.0
        self.entry_spring.zeta = 0.76
        self.entry_spring.current = 0.0
        self.entry_spring.target = 1.0
        self.entry_spring.velocity = 0.0
        self.search_active = True
        self.cursor_idx = len(self.search_query)

        if self.cursor_timer_id is None:
            self.cursor_timer_id = GLib.timeout_add(500, self._on_cursor_blink_timer)

        self.show_all()
        self.present()
        self.im_context.focus_in()
        self._request_frame()

    def dismiss_window(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        self._suppress_hover = True
        self.hovered_card_idx = None
        self.hover_cat_idx = None
        if self.cursor_timer_id is not None:
            GLib.source_remove(self.cursor_timer_id)
            self.cursor_timer_id = None
        self.im_context.focus_out()
        self.entry_spring.omega = 19.0
        self.entry_spring.zeta = 0.88
        self.entry_spring.target = 0.0
        self._request_frame()

    def _finish_dismiss(self):
        if self.cursor_timer_id is not None:
            GLib.source_remove(self.cursor_timer_id)
            self.cursor_timer_id = None
        self.scanner.shutdown()
        release_instance_lock(self.lock_fd, self.pid_path)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()

    def _request_frame(self):
        if self.tick_callback_id is None:
            self.last_frame_time = 0
            self.tick_callback_id = self.add_tick_callback(self.on_frame_tick)

    def on_frame_tick(self, widget, frame_clock):
        frame_time = frame_clock.get_frame_time()
        dt = 0.016 if self.last_frame_time == 0 else (frame_time - self.last_frame_time) / 1_000_000.0
        self.last_frame_time = frame_time

        still_animating = False

        if self.entry_spring.update(dt):
            still_animating = True

        if self.is_dismissing and self.entry_spring.current <= 0.005:
            self._finish_dismiss()
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        # Update smooth scrolling spring
        self.scroll_spring.target = self.target_scroll_y
        if self.scroll_spring.update(dt):
            still_animating = True

        # Update active card elevation springs
        active_keys = list(self.card_springs.keys())
        for idx in active_keys:
            is_hl = (self.hovered_card_idx == idx or self.keyboard_selected_idx == idx) and not self.is_dismissing
            self.card_springs[idx].target = 1.0 if is_hl else 0.0
            if self.card_springs[idx].update(dt):
                still_animating = True
            elif not is_hl and abs(self.card_springs[idx].current) < 0.005:
                del self.card_springs[idx]

        self.queue_draw()

        if not still_animating:
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def get_current_items(self) -> list:
        """Get filtered wallpaper items based on active category and search query."""
        cache_key = (self.search_query.strip().lower(), self.active_cat_idx)
        if self._cached_items_key == cache_key and self._cached_items is not None:
            return self._cached_items

        if self.search_query.strip():
            q = self.search_query.strip().lower()
            result = [it for it in self.scanner.items if q in it.title.lower() or q in it.filename.lower()]
        elif 0 <= self.active_cat_idx < len(self.scanner.categories):
            cat_name = self.scanner.categories[self.active_cat_idx]
            result = self.scanner.category_items.get(cat_name, [])
        else:
            result = self.scanner.items

        self._cached_items = result
        self._cached_items_key = cache_key
        return result

    def select_and_apply(self, item):
        """Apply selected wallpaper in background thread and dismiss immediately."""
        self.dismiss_window()
        threading.Thread(target=apply_wallpaper, args=(item,), daemon=False).start()

    def get_max_scroll_y(self) -> float:
        """Calculate maximum vertical scroll offset for current item collection."""
        items = self.get_current_items()
        total_rows = math.ceil(len(items) / GRID_COLS)
        total_h = total_rows * (CARD_HEIGHT + GAP_Y)
        return max(0.0, total_h - GRID_VIEWPORT_H + 16.0)

    def scroll_to_make_visible(self, item_idx: int):
        """Adjust target_scroll_y to ensure the focused card is visible within the viewport."""
        row = item_idx // GRID_COLS
        card_top = row * (CARD_HEIGHT + GAP_Y)
        card_bottom = card_top + CARD_HEIGHT

        curr_view_top = self.target_scroll_y
        curr_view_bottom = curr_view_top + GRID_VIEWPORT_H

        if card_top < curr_view_top:
            self.target_scroll_y = card_top
        elif card_bottom > curr_view_bottom:
            self.target_scroll_y = card_bottom - GRID_VIEWPORT_H + 16.0

        max_scroll = self.get_max_scroll_y()
        self.target_scroll_y = max(0.0, min(max_scroll, self.target_scroll_y))
        self._request_frame()

    def on_draw(self, widget, cr):
        entry_val = max(0.0, min(1.0, self.entry_spring.current))
        if entry_val <= 0.001:
            return False

        win_w = self.get_allocated_width() or 1920
        win_h = self.get_allocated_height() or 1080

        # Hermite smoothstep cubic curve for silky non-linear alpha & spatial scale
        t = entry_val
        alpha = t * t * (3.0 - 2.0 * t)
        scale = 0.96 + 0.04 * t

        dialog_w = min(WIN_WIDTH, win_w - 40.0)
        dialog_h = min(WIN_HEIGHT, win_h - 40.0)
        dialog_x = (win_w - dialog_w) / 2.0
        dialog_y = (win_h - dialog_h) / 2.0 + (1.0 - t) * 12.0

        # Render dialog in an isolated group with smooth centered micro-scale transform
        cr.save()
        cr.translate(win_w / 2.0, win_h / 2.0)
        cr.scale(scale, scale)
        cr.translate(-win_w / 2.0, -win_h / 2.0)
        cr.push_group()

        # Dialog Frosted Glass Container with Multi-Tier Diffuse Shadow
        draw_dialog_container(cr, dialog_x, dialog_y, dialog_w, dialog_h, WIN_RADIUS, self.palette)

        # Top Header & Pro-Grade Search Pill
        all_count = len(self.scanner.items)
        self.search_box, self.clear_box, cursor_rect = draw_header(
            cr, dialog_x, dialog_y, dialog_w,
            total_count=all_count,
            search_query=self.search_query,
            search_active=self.search_active,
            cursor_idx=self.cursor_idx,
            cursor_time=self.cursor_time,
            palette=self.palette,
            create_layout_fn=self.create_pango_layout
        )

        # Sync Wayland CJK IME cursor location precisely under caret
        if self.search_active and cursor_rect:
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = int(cursor_rect[0]), int(cursor_rect[1]), int(cursor_rect[2]), int(cursor_rect[3])
            self.im_context.set_cursor_location(rect)

        # Category Chips
        chips_y = dialog_y + 70.0
        self.chip_boxes = draw_category_chips(
            cr, dialog_x, chips_y, dialog_w,
            categories=self.scanner.categories,
            active_cat_idx=self.active_cat_idx,
            hover_cat_idx=self.hover_cat_idx,
            palette=self.palette,
            create_layout_fn=self.create_pango_layout
        )

        # Continuous Scrollable Card Grid
        grid_x = dialog_x + 32.0
        grid_y = dialog_y + GRID_VIEWPORT_Y
        grid_w = dialog_w - 64.0
        grid_h = GRID_VIEWPORT_H

        scroll_y = self.scroll_spring.current
        items = self.get_current_items()
        max_scroll_y = self.get_max_scroll_y()

        first_visible_row = max(0, int(scroll_y // (CARD_HEIGHT + GAP_Y)))
        last_visible_row = int((scroll_y + GRID_VIEWPORT_H) // (CARD_HEIGHT + GAP_Y)) + 2
        first_visible_idx = first_visible_row * GRID_COLS
        last_visible_idx = min(last_visible_row * GRID_COLS + GRID_COLS, len(items))
        if items and first_visible_idx < len(items):
            self.scanner.load_visible_thumbnails(items[first_visible_idx:last_visible_idx])

        # Viewport clipping with safe padding
        cr.save()
        cr.rectangle(dialog_x + 16.0, grid_y, dialog_w - 32.0, grid_h)
        cr.clip()

        self.card_boxes = []

        for idx, item in enumerate(items):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            cx = grid_x + col * (CARD_WIDTH + GAP_X)
            cy = grid_y + 8.0 + row * (CARD_HEIGHT + GAP_Y) - scroll_y

            self.card_boxes.append((cx, cy, CARD_WIDTH, CARD_HEIGHT))

            # Render visible cards
            if cy + CARD_HEIGHT >= grid_y - 20.0 and cy <= grid_y + grid_h + 20.0:
                is_cur = (item.path == self.current_wp_path)
                is_active = (self.keyboard_selected_idx == idx)
                is_hover = (self.hovered_card_idx == idx)

                if is_active or is_hover:
                    if idx not in self.card_springs:
                        self.card_springs[idx] = Spring(0.0, omega=26.0, zeta=0.92)
                hover_val = self.card_springs[idx].current if idx in self.card_springs else 0.0

                draw_card(
                    cr, cx, cy, CARD_WIDTH, CARD_HEIGHT, item,
                    is_active=is_active,
                    is_hovered=is_hover,
                    is_current=is_cur,
                    hover_val=hover_val,
                    palette=self.palette,
                    create_layout_fn=self.create_pango_layout
                )

        cr.restore()

        # Minimalist Scrollbar Indicator
        sb_x = dialog_x + dialog_w - 20.0
        draw_scrollbar(cr, sb_x, grid_y, grid_h, scroll_y, max_scroll_y, self.palette)

        # Composite the entire dialog group seamlessly with Hermite cubic alpha
        cr.pop_group_to_source()
        cr.paint_with_alpha(alpha)
        cr.restore()

        if self.hovered_card_idx is None and not self.is_dismissing and not self._suppress_hover:
            self._update_hover_from_pointer()

        return False

    def on_im_commit(self, im_context, text):
        self.search_active = True
        self.cursor_time = 0.0
        self.search_query = self.search_query[:self.cursor_idx] + text + self.search_query[self.cursor_idx:]
        self.cursor_idx += len(text)
        self.target_scroll_y = 0.0
        self.keyboard_selected_idx = 0
        self._request_frame()

    def _check_hover(self, mx: float, my: float):
        if self.is_dismissing or self._suppress_hover:
            return

        # Check Category Chips
        new_hover_cat = None
        for idx, (bx, by, bw, bh) in enumerate(self.chip_boxes):
            if bx <= mx <= bx + bw and by <= my <= by + bh:
                new_hover_cat = idx
                break

        if new_hover_cat != self.hover_cat_idx:
            self.hover_cat_idx = new_hover_cat
            self._request_frame()

        # Check Cards
        new_hover_card = None
        items = self.get_current_items()
        for idx, (bx, by, bw, bh) in enumerate(self.card_boxes):
            if idx < len(items) and bx <= mx <= bx + bw and by <= my <= by + bh:
                new_hover_card = idx
                break

        if new_hover_card != self.hovered_card_idx:
            self.hovered_card_idx = new_hover_card
            self._request_frame()

    def _update_hover_from_pointer(self):
        if self.is_dismissing or self._suppress_hover:
            return
        gdk_window = self.get_window()
        if not gdk_window:
            return
        try:
            display = gdk_window.get_display()
            seat = display.get_default_seat() if display else None
            pointer = seat.get_pointer() if seat else None
            if pointer:
                _, mx, my, _ = gdk_window.get_device_position_double(pointer)
                self._check_hover(mx, my)
        except Exception:
            pass

    def on_motion_notify(self, widget, event):
        if self.is_dismissing or self._suppress_hover:
            return True
        self._check_hover(event.x, event.y)
        return True

    def on_button_press(self, widget, event):
        if self.is_dismissing:
            return True

        # Right-click -> Dismiss or clear search
        if event.button in (2, 3):
            if self.search_query:
                self.search_query = ""
                self.cursor_idx = 0
                self.search_active = True
                self.target_scroll_y = 0.0
                self._request_frame()
            else:
                self.dismiss_window()
            return True

        # Left-click
        if event.button == 1:
            mx, my = event.x, event.y

            # 1. Clicked Clear '×' button
            if self.clear_box:
                cx, cy, cw, ch = self.clear_box
                if cx <= mx <= cx + cw and cy <= my <= cy + ch:
                    self.search_query = ""
                    self.cursor_idx = 0
                    self.search_active = True
                    self.target_scroll_y = 0.0
                    self.keyboard_selected_idx = 0
                    self._request_frame()
                    return True

            # 2. Clicked Search Pill
            if self.search_box:
                sx, sy, sw, sh = self.search_box
                if sx <= mx <= sx + sw and sy <= my <= sy + sh:
                    self.search_active = True
                    self.cursor_idx = len(self.search_query)
                    self._request_frame()
                    return True

            # 3. Clicked category chip
            for idx, (bx, by, bw, bh) in enumerate(self.chip_boxes):
                if bx <= mx <= bx + bw and by <= my <= by + bh:
                    self.active_cat_idx = idx
                    self.target_scroll_y = 0.0
                    self.keyboard_selected_idx = None
                    self._request_frame()
                    self._update_hover_from_pointer()
                    return True

            # 4. Clicked card
            items = self.get_current_items()
            for idx, (bx, by, bw, bh) in enumerate(self.card_boxes):
                if idx < len(items) and bx <= mx <= bx + bw and by <= my <= by + bh:
                    self.select_and_apply(items[idx])
                    return True

            # 5. Clicked outside dialog -> dismiss
            win_w = self.get_allocated_width() or 1920
            win_h = self.get_allocated_height() or 1080
            dialog_w = min(WIN_WIDTH, win_w - 40.0)
            dialog_h = min(WIN_HEIGHT, win_h - 40.0)
            dialog_x = (win_w - dialog_w) / 2.0
            dialog_y = (win_h - dialog_h) / 2.0
            if not (dialog_x <= mx <= dialog_x + dialog_w and dialog_y <= my <= dialog_y + dialog_h):
                self.dismiss_window()
                return True

        return False

    def on_scroll(self, widget, event):
        """Handle smooth continuous scrolling for both touchpad and mouse wheel."""
        if self.is_dismissing:
            return False

        max_scroll_y = self.get_max_scroll_y()
        if max_scroll_y <= 0:
            return False

        handled = False
        # 1. High-precision Touchpad & Smooth Wheel
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            success, dx, dy = event.get_scroll_deltas()
            if success:
                self.target_scroll_y += dy * 45.0
                self.target_scroll_y = max(0.0, min(max_scroll_y, self.target_scroll_y))
                self._request_frame()
                handled = True

        # 2. Discrete Mouse Wheel
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.target_scroll_y += 120.0
            self.target_scroll_y = max(0.0, min(max_scroll_y, self.target_scroll_y))
            self._request_frame()
            handled = True
        elif event.direction == Gdk.ScrollDirection.UP:
            self.target_scroll_y -= 120.0
            self.target_scroll_y = max(0.0, min(max_scroll_y, self.target_scroll_y))
            self._request_frame()
            handled = True

        if handled:
            self._update_hover_from_pointer()
            return True

        return False

    def on_key_press(self, widget, event):
        if self.is_dismissing:
            return True

        keyval = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)

        # 1. IME Processing
        if self.im_context.filter_keypress(event):
            return True

        # 2. Ctrl Shortcuts
        if ctrl:
            if keyval in (Gdk.KEY_r, Gdk.KEY_R):
                items = self.get_current_items()
                if items:
                    target = random.choice(items)
                    self.select_and_apply(target)
                return True
            elif keyval in (Gdk.KEY_v, Gdk.KEY_V):
                clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                text = clip.wait_for_text()
                if text:
                    self.search_active = True
                    self.search_query = self.search_query[:self.cursor_idx] + text.strip() + self.search_query[self.cursor_idx:]
                    self.cursor_idx += len(text.strip())
                    self.target_scroll_y = 0.0
                    self.keyboard_selected_idx = 0
                    self._request_frame()
                return True
            elif keyval in (Gdk.KEY_c, Gdk.KEY_C):
                if self.search_query:
                    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                    clip.set_text(self.search_query, -1)
                return True
            elif keyval in (Gdk.KEY_u, Gdk.KEY_U):
                self.search_query = ""
                self.cursor_idx = 0
                self.target_scroll_y = 0.0
                self.keyboard_selected_idx = 0
                self._request_frame()
                return True
            elif keyval in (Gdk.KEY_w, Gdk.KEY_W):
                before = self.search_query[:self.cursor_idx]
                after = self.search_query[self.cursor_idx:]
                words = before.rstrip().rsplit(None, 1)
                new_before = words[0] if len(words) > 1 else ""
                self.cursor_idx = len(new_before)
                self.search_query = new_before + after
                self.target_scroll_y = 0.0
                self._request_frame()
                return True

        # 3. Escape
        if keyval == Gdk.KEY_Escape:
            if self.search_query:
                self.search_query = ""
                self.cursor_idx = 0
                self.target_scroll_y = 0.0
                self._request_frame()
            else:
                self.dismiss_window()
            return True

        # 4. Cursor Left / Right / Home / End
        if keyval == Gdk.KEY_Left:
            if self.search_active and self.search_query:
                if self.cursor_idx > 0:
                    self.cursor_idx -= 1
                    self._request_frame()
                return True
            items = self.get_current_items()
            num_items = len(items)
            if num_items == 0:
                return True
            if self.keyboard_selected_idx is None:
                self.keyboard_selected_idx = 0
            else:
                col = self.keyboard_selected_idx % GRID_COLS
                if col > 0 and self.keyboard_selected_idx - 1 >= 0:
                    self.keyboard_selected_idx -= 1
            self.scroll_to_make_visible(self.keyboard_selected_idx)
            self._request_frame()
            return True
        elif keyval == Gdk.KEY_Right:
            if self.search_active and self.search_query:
                if self.cursor_idx < len(self.search_query):
                    self.cursor_idx += 1
                    self._request_frame()
                return True
            items = self.get_current_items()
            num_items = len(items)
            if num_items == 0:
                return True
            if self.keyboard_selected_idx is None:
                self.keyboard_selected_idx = 0
            else:
                col = self.keyboard_selected_idx % GRID_COLS
                if col < GRID_COLS - 1 and self.keyboard_selected_idx + 1 < num_items:
                    self.keyboard_selected_idx += 1
            self.scroll_to_make_visible(self.keyboard_selected_idx)
            self._request_frame()
            return True
        elif keyval == Gdk.KEY_Home:
            if self.search_active and self.search_query:
                self.cursor_idx = 0
                self._request_frame()
                return True
            self.keyboard_selected_idx = 0
            self.scroll_to_make_visible(0)
            self._request_frame()
            return True
        elif keyval == Gdk.KEY_End:
            if self.search_active and self.search_query:
                self.cursor_idx = len(self.search_query)
                self._request_frame()
                return True
            items = self.get_current_items()
            num_items = len(items)
            if num_items > 0:
                self.keyboard_selected_idx = num_items - 1
                self.scroll_to_make_visible(self.keyboard_selected_idx)
                self._request_frame()
            return True

        # 5. Backspace & Delete at Cursor Index
        if keyval == Gdk.KEY_BackSpace:
            if self.cursor_idx > 0:
                self.cursor_time = 0.0
                self.search_query = self.search_query[:self.cursor_idx - 1] + self.search_query[self.cursor_idx:]
                self.cursor_idx -= 1
                self.target_scroll_y = 0.0
                self.keyboard_selected_idx = 0
                self._request_frame()
            elif not self.search_query:
                self.dismiss_window()
            return True

        if keyval == Gdk.KEY_Delete:
            if self.cursor_idx < len(self.search_query):
                self.cursor_time = 0.0
                self.search_query = self.search_query[:self.cursor_idx] + self.search_query[self.cursor_idx + 1:]
                self.target_scroll_y = 0.0
                self._request_frame()
            return True

        # 6. Tab / Shift+Tab for Category Chips
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            step = -1 if bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab else 1
            self.active_cat_idx = (self.active_cat_idx + step) % len(self.scanner.categories)
            self.target_scroll_y = 0.0
            self.keyboard_selected_idx = None
            self._request_frame()
            self._update_hover_from_pointer()
            return True

        # 7. Navigation (Arrow Down / Up -> Select within Card Grid)
        items = self.get_current_items()
        num_items = len(items)

        if keyval == Gdk.KEY_Down:
            if num_items == 0:
                return True
            if self.keyboard_selected_idx is None:
                self.keyboard_selected_idx = 0
            elif self.keyboard_selected_idx + GRID_COLS < num_items:
                self.keyboard_selected_idx += GRID_COLS
            else:
                self.keyboard_selected_idx = num_items - 1
            self.scroll_to_make_visible(self.keyboard_selected_idx)
            self._request_frame()
            return True
        elif keyval == Gdk.KEY_Up:
            if num_items == 0:
                return True
            if self.keyboard_selected_idx is None:
                self.keyboard_selected_idx = 0
            elif self.keyboard_selected_idx >= GRID_COLS:
                self.keyboard_selected_idx -= GRID_COLS
            else:
                self.keyboard_selected_idx = 0
            self.scroll_to_make_visible(self.keyboard_selected_idx)
            self._request_frame()
            return True

        # 8. Enter -> Apply selected wallpaper
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.keyboard_selected_idx is not None and 0 <= self.keyboard_selected_idx < num_items:
                self.select_and_apply(items[self.keyboard_selected_idx])
            elif num_items > 0:
                self.select_and_apply(items[0])
            return True

        # 9. Printable Text Typing (Inserted at cursor_idx)
        if 32 <= keyval <= 126 and not ctrl:
            char = chr(keyval)
            self.cursor_time = 0.0
            self.search_query = self.search_query[:self.cursor_idx] + char + self.search_query[self.cursor_idx:]
            self.cursor_idx += 1
            self.target_scroll_y = 0.0
            self.keyboard_selected_idx = 0
            self._request_frame()
            return True

        return False
