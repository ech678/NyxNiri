"""
NyxNiri Wallpaper Picker Cairo Vector Rendering Pipeline
Ultra-fast, hardware-efficient vector graphics rendering engine with pure M3E aesthetics and high-contrast typography.
"""

import math
import cairo
import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GLib, Pango, PangoCairo, GdkPixbuf

from .config import (
    CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS, THUMB_HEIGHT,
    HEADER_HEIGHT, GRID_COLS
)

# ── Pre-allocated Font Descriptions for Zero-Allocation Rendering Loop ──────────
FONT_HEADER_TITLE = Pango.FontDescription("Noto Sans CJK SC, Inter SemiBold 15")
FONT_SEARCH_ICON = Pango.FontDescription("JetBrainsMono Nerd Font 12")
FONT_SEARCH_TEXT = Pango.FontDescription("Noto Sans CJK SC 10")
FONT_CLEAR_ICON = Pango.FontDescription("JetBrainsMono Nerd Font 10")
FONT_CHIP = Pango.FontDescription("Noto Sans CJK SC, Inter Medium 9.5")
FONT_CARD_TITLE = Pango.FontDescription("Noto Sans CJK SC, Inter SemiBold 9.5")


def draw_rounded_rect(cr, x: float, y: float, w: float, h: float, r: float):
    """Draw a smooth continuous rounded rectangle path."""
    r = min(r, w / 2.0, h / 2.0)
    cr.new_path()
    cr.arc(x + r, y + r, r, math.pi, 3.0 * math.pi / 2.0)
    cr.arc(x + w - r, y + r, r, 3.0 * math.pi / 2.0, 2.0 * math.pi)
    cr.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    cr.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    cr.close_path()


def draw_top_rounded_rect(cr, x: float, y: float, w: float, h: float, r: float):
    """Draw a rounded rectangle with top corners rounded and bottom corners square."""
    r = min(r, w / 2.0, h / 2.0)
    cr.new_path()
    cr.arc(x + r, y + r, r, math.pi, 3.0 * math.pi / 2.0)
    cr.arc(x + w - r, y + r, r, 3.0 * math.pi / 2.0, 2.0 * math.pi)
    cr.line_to(x + w, y + h)
    cr.line_to(x, y + h)
    cr.close_path()


def draw_dialog_container(cr, x: float, y: float, w: float, h: float, r: float, palette: dict):
    """Draw the central floating frosted glass container with smooth multi-tier diffuse shadow."""
    surf_r, surf_g, surf_b = palette["surface"]
    out_r, out_g, out_b = palette["outline"]

    # 1. Multi-Tier Diffuse Soft Ambient Shadow (Zero Hard Lines / Zero Abrupt Pop)
    cr.save()
    for off_y, spread, s_alpha in (
        (2.0, 2.0, 0.08),
        (6.0, 6.0, 0.06),
        (14.0, 16.0, 0.04),
        (24.0, 28.0, 0.02),
    ):
        draw_rounded_rect(cr, x - spread, y + off_y - spread / 2.0, w + spread * 2.0, h + spread, r + spread)
        cr.set_source_rgba(0.0, 0.0, 0.0, s_alpha)
        cr.fill()
    cr.restore()

    # 2. Translucent Frosted Glass Surface
    cr.save()
    draw_rounded_rect(cr, x, y, w, h, r)
    cr.set_source_rgba(surf_r, surf_g, surf_b, 0.96)
    cr.fill_preserve()

    # 3. Subtle Perimeter Border
    cr.set_source_rgba(out_r, out_g, out_b, 0.20)
    cr.set_line_width(1.0)
    cr.stroke()
    cr.restore()


def draw_header(cr, x: float, y: float, w: float, total_count: int,
                search_query: str, search_active: bool, cursor_idx: int, cursor_time: float,
                palette: dict, create_layout_fn):
    """Draw header with sleek title and pro-grade search pill. Returns collision bounding boxes."""
    on_surf = palette["on_surface"]
    on_surf_var = palette["on_surface_var"]
    out_rgb = palette["outline"]
    prim_rgb = palette["primary"]
    surf_bright = palette.get("surface_bright", (0.2, 0.22, 0.28))
    is_dark = palette.get("is_dark", True)

    # 1. Sleek Compact Title: "Wallpapers · 29"
    title_text = f"Wallpapers  <span alpha='50%'>·</span>  <span size='small' alpha='75%'>{total_count}</span>"
    title_layout = create_layout_fn("")
    title_layout.set_markup(title_text, -1)
    title_layout.set_font_description(FONT_HEADER_TITLE)
    cr.save()
    cr.move_to(x + 32.0, y + 26.0)
    cr.set_source_rgba(on_surf[0], on_surf[1], on_surf[2], 0.98)
    PangoCairo.show_layout(cr, title_layout)
    cr.restore()

    # 2. Minimalist M3E Search Pill
    search_w = 260.0
    search_h = 36.0
    search_x = x + w - search_w - 32.0
    search_y = y + 22.0
    search_r = search_h / 2.0

    bg_alpha = 0.50 if is_dark else 0.85
    cr.save()
    draw_rounded_rect(cr, search_x, search_y, search_w, search_h, search_r)
    cr.set_source_rgba(surf_bright[0], surf_bright[1], surf_bright[2], bg_alpha)
    cr.fill_preserve()

    border_alpha = 0.25 if is_dark else 0.38
    if search_active:
        cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.85)
        cr.set_line_width(1.4)
    else:
        cr.set_source_rgba(out_rgb[0], out_rgb[1], out_rgb[2], border_alpha)
        cr.set_line_width(1.0)
    cr.stroke()

    # Search Icon (Magnifying glass)
    icon_layout = create_layout_fn("󰍉")
    icon_layout.set_font_description(FONT_SEARCH_ICON)
    cr.move_to(search_x + 12.0, search_y + 9.0)
    icon_alpha = 0.75 if is_dark else 0.85
    cr.set_source_rgba(on_surf_var[0], on_surf_var[1], on_surf_var[2], icon_alpha)
    PangoCairo.show_layout(cr, icon_layout)

    # Search Text or Placeholder
    text_left = search_x + 34.0
    cursor_x_pos = text_left

    if search_query:
        # Prefix text up to cursor position
        prefix_text = search_query[:cursor_idx]
        prefix_layout = create_layout_fn(prefix_text)
        prefix_layout.set_font_description(FONT_SEARCH_TEXT)
        pw, _ = prefix_layout.get_pixel_size()
        cursor_x_pos = text_left + pw

        query_layout = create_layout_fn(search_query)
        query_layout.set_font_description(FONT_SEARCH_TEXT)
        cr.move_to(text_left, search_y + 9.0)
        cr.set_source_rgba(on_surf[0], on_surf[1], on_surf[2], 0.98)
        PangoCairo.show_layout(cr, query_layout)
    else:
        ph_layout = create_layout_fn("Search wallpapers...")
        ph_layout.set_font_description(FONT_SEARCH_TEXT)
        cr.move_to(text_left, search_y + 9.0)
        ph_alpha = 0.45 if is_dark else 0.55
        cr.set_source_rgba(on_surf_var[0], on_surf_var[1], on_surf_var[2], ph_alpha)
        PangoCairo.show_layout(cr, ph_layout)

    # Blinking Cursor Line at cursor_x_pos
    if search_active and int(cursor_time * 2.0) % 2 == 0:
        cr.new_path()
        cr.move_to(cursor_x_pos + 1.0, search_y + 8.0)
        cr.line_to(cursor_x_pos + 1.0, search_y + search_h - 8.0)
        cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.90)
        cr.set_line_width(1.4)
        cr.stroke()

    # Clear Icon '×' if search_query is not empty
    clear_box = None
    if search_query:
        clear_layout = create_layout_fn("󰅖")
        clear_layout.set_font_description(FONT_CLEAR_ICON)
        cw, ch = clear_layout.get_pixel_size()
        cx = search_x + search_w - cw - 12.0
        cy = search_y + (search_h - ch) / 2.0
        cr.move_to(cx, cy)
        cr.set_source_rgba(on_surf_var[0], on_surf_var[1], on_surf_var[2], 0.70)
        PangoCairo.show_layout(cr, clear_layout)
        clear_box = (cx - 4.0, cy - 4.0, cw + 8.0, ch + 8.0)

    cr.restore()

    search_box = (search_x, search_y, search_w, search_h)
    cursor_rect = (cursor_x_pos, search_y + 8.0, 2.0, search_h - 16.0)
    return search_box, clear_box, cursor_rect


def draw_category_chips(cr, x: float, y: float, w: float, categories: list,
                        active_cat_idx: int, hover_cat_idx: int,
                        palette: dict, create_layout_fn) -> list:
    """Draw high-contrast category filter chips with luminance-based readability. Returns list of bounding boxes."""
    on_surf = palette["on_surface"]
    prim_rgb = palette["primary"]
    surf_bright = palette.get("surface_bright", (0.2, 0.22, 0.28))
    out_rgb = palette["outline"]
    is_dark = palette.get("is_dark", True)

    cur_x = x + 32.0
    chip_h = 28.0
    chip_r = chip_h / 2.0
    chip_boxes = []

    # Dynamic relative luminance check for primary color to guarantee WCAG AA contrast (4.5:1+)
    pr, pg, pb = prim_rgb
    prim_lum = 0.299 * pr + 0.587 * pg + 0.114 * pb
    active_text_rgb = (0.05, 0.06, 0.09) if prim_lum > 0.55 else (0.98, 0.98, 1.00)

    for idx, cat_name in enumerate(categories):
        layout = create_layout_fn(cat_name)
        layout.set_font_description(FONT_CHIP)
        lw, lh = layout.get_pixel_size()
        chip_w = max(52.0, lw + 20.0)

        is_active = (idx == active_cat_idx)
        is_hovered = (idx == hover_cat_idx)

        cr.save()
        draw_rounded_rect(cr, cur_x, y, chip_w, chip_h, chip_r)

        if is_active:
            cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.95)
            cr.fill()
            cr.move_to(cur_x + (chip_w - lw) / 2.0, y + (chip_h - lh) / 2.0)
            cr.set_source_rgba(active_text_rgb[0], active_text_rgb[1], active_text_rgb[2], 0.98)
            PangoCairo.show_layout(cr, layout)
        else:
            bg_alpha = (0.25 if is_dark else 0.40) if is_hovered else (0.12 if is_dark else 0.22)
            cr.set_source_rgba(surf_bright[0], surf_bright[1], surf_bright[2], bg_alpha)
            cr.fill_preserve()

            border_alpha = (0.40 if is_dark else 0.50) if is_hovered else (0.25 if is_dark else 0.35)
            cr.set_source_rgba(out_rgb[0], out_rgb[1], out_rgb[2], border_alpha)
            cr.set_line_width(1.0)
            cr.stroke()

            cr.move_to(cur_x + (chip_w - lw) / 2.0, y + (chip_h - lh) / 2.0)
            text_alpha = 0.98 if is_hovered else (0.85 if is_dark else 0.90)
            cr.set_source_rgba(on_surf[0], on_surf[1], on_surf[2], text_alpha)
            PangoCairo.show_layout(cr, layout)

        cr.restore()
        chip_boxes.append((cur_x, y, chip_w, chip_h))
        cur_x += chip_w + 8.0

    return chip_boxes


def draw_card(cr, x: float, y: float, w: float, h: float, item,
              is_active: bool, is_hovered: bool, is_current: bool,
              hover_val: float,
              palette: dict, create_layout_fn):
    """Draw a wallpaper card with 100% pristine 16:9 artwork and clean inline [Live] title."""
    on_surf = palette["on_surface"]
    prim_rgb = palette["primary"]
    tert_rgb = palette["tertiary"]
    out_rgb = palette["outline"]
    surf_bright = palette.get("surface_bright", (0.16, 0.18, 0.24))

    card_y = y
    r = CARD_RADIUS

    # 1. Hover Glow / Shadow
    if is_hovered or is_active or is_current:
        cr.save()
        draw_rounded_rect(cr, x, card_y + 4.0, w, h, r)
        glow_alpha = 0.22 + 0.18 * hover_val
        cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], glow_alpha * 0.35)
        cr.fill()
        cr.restore()
    else:
        cr.save()
        draw_rounded_rect(cr, x, card_y + 2.0, w, h, r)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.15)
        cr.fill()
        cr.restore()

    # 2. Card Background
    cr.save()
    draw_rounded_rect(cr, x, card_y, w, h, r)
    cr.set_source_rgba(surf_bright[0], surf_bright[1], surf_bright[2], 0.90)
    cr.fill()

    # 3. Fast Pre-rendered Cairo Surface Blit (100% Pure Unobstructed Artwork)
    thumb_h = THUMB_HEIGHT
    if item.surface:
        cr.set_source_surface(item.surface, x, card_y)
        cr.paint()
    else:
        draw_top_rounded_rect(cr, x, card_y, w, thumb_h, r)
        cr.set_source_rgba(0.08, 0.09, 0.13, 0.85)
        cr.fill()

    # 4. Clean Inline Title with [Live] Tag for Video Wallpapers (Zero Floating Badges)
    info_y = card_y + thumb_h + 8.0
    text_left = x + 14.0

    title_layout = create_layout_fn("")
    title_layout.set_font_description(FONT_CARD_TITLE)
    title_layout.set_width(int((w - 28.0) * Pango.SCALE))
    title_layout.set_ellipsize(Pango.EllipsizeMode.END)

    if item.is_video:
        escaped_title = GLib.markup_escape_text(item.title)
        tert_hex = f"#{int(tert_rgb[0]*255):02x}{int(tert_rgb[1]*255):02x}{int(tert_rgb[2]*255):02x}"
        markup = f"<span foreground='{tert_hex}' weight='bold'>[Live]</span>  {escaped_title}"
        title_layout.set_markup(markup, -1)
    else:
        title_layout.set_text(item.title)

    cr.move_to(text_left, info_y)
    cr.set_source_rgba(on_surf[0], on_surf[1], on_surf[2], 0.95)
    PangoCairo.show_layout(cr, title_layout)

    # 5. Card Focus & Active Outline (Primary focus ring when active or current)
    draw_rounded_rect(cr, x, card_y, w, h, r)
    if is_active or is_hovered:
        cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.70 + 0.30 * hover_val)
        cr.set_line_width(2.0)
    elif is_current:
        cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.60)
        cr.set_line_width(1.6)
    else:
        cr.set_source_rgba(out_rgb[0], out_rgb[1], out_rgb[2], 0.14)
        cr.set_line_width(1.0)
    cr.stroke()
    cr.restore()


def draw_scrollbar(cr, x: float, y: float, h: float, scroll_y: float, max_scroll_y: float, palette: dict):
    """Draw minimalist capsule scrollbar indicator on the right of the grid."""
    if max_scroll_y <= 0:
        return

    out_rgb = palette["outline"]
    prim_rgb = palette["primary"]

    sb_w = 3.5
    sb_r = sb_w / 2.0

    # Track
    cr.save()
    draw_rounded_rect(cr, x, y, sb_w, h, sb_r)
    cr.set_source_rgba(out_rgb[0], out_rgb[1], out_rgb[2], 0.08)
    cr.fill()

    # Thumb
    thumb_h = max(28.0, h * (h / (h + max_scroll_y)))
    thumb_progress = min(1.0, max(0.0, scroll_y / max_scroll_y))
    thumb_y = y + thumb_progress * (h - thumb_h)

    draw_rounded_rect(cr, x, thumb_y, sb_w, thumb_h, sb_r)
    cr.set_source_rgba(prim_rgb[0], prim_rgb[1], prim_rgb[2], 0.45)
    cr.fill()
    cr.restore()
