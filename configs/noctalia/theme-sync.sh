#!/usr/bin/env bash
# ==============================================================================
# NyxNiri System Theme Dispatcher & Bus (theme-sync.sh)
# High-robustness, atomic, zero-entropy theme synchronization engine.
# ==============================================================================

set -uo pipefail

# 1. Portability: Overridable theme configuration variables
GTK_THEME_DARK="${NYXNIRI_GTK_THEME_DARK:-adw-gtk3-dark}"
GTK_THEME_LIGHT="${NYXNIRI_GTK_THEME_LIGHT:-adw-gtk3}"
KVANTUM_THEME_DARK="${NYXNIRI_KVANTUM_DARK:-KvLibadwaitaDark}"
KVANTUM_THEME_LIGHT="${NYXNIRI_KVANTUM_LIGHT:-KvLibadwaita}"
DEFAULT_FALLBACK_MODE="${NYXNIRI_DEFAULT_MODE:-dark}"

# 2. Concurrency Lock: Prevent race conditions from rapid toggles or startup hooks
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/nyxniri-theme-sync.lock"
exec 9>"$LOCK_FILE"
flock -w 5 9 || {
    echo "[!] Theme sync locked by another process. Skipping." >&2
    exit 0
}

# 3. Atomic INI Setting Updater (Safe against whitespace, regex chars, and powerloss)
atomic_update_ini() {
    local file="$1"
    local key="$2"
    local val="$3"

    local dir
    dir="$(dirname "$file")"
    mkdir -p "$dir" 2>/dev/null || true

    local tmp_file
    tmp_file=$(mktemp "$dir/.ini.XXXXXX") || return 1

    local key_found=0
    local has_settings_header=0
    local escaped_key
    escaped_key=$(printf '%s' "$key" | sed 's/[][\.^$*+?(){}|/]/\\&/g')

    if [ -f "$file" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^\[Settings\] ]]; then
                has_settings_header=1
                echo "$line" >> "$tmp_file"
                continue
            fi
            if [[ "$line" =~ ^[[:space:]]*${escaped_key}[[:space:]]*= ]]; then
                echo "${key}=${val}" >> "$tmp_file"
                key_found=1
            else
                echo "$line" >> "$tmp_file"
            fi
        done < "$file"
    fi

    if [ "$key_found" -eq 0 ]; then
        if [ "$has_settings_header" -eq 0 ] && [ ! -s "$tmp_file" ]; then
            echo "[Settings]" > "$tmp_file"
        fi
        echo "${key}=${val}" >> "$tmp_file"
    fi

    chmod 644 "$tmp_file" 2>/dev/null || true
    mv -f "$tmp_file" "$file"
}

# 4. Safe GSettings / dconf Setter
set_system_theme() {
    local scheme="$1"
    local gtk_theme="$2"

    if command -v gsettings >/dev/null 2>&1; then
        gsettings set org.gnome.desktop.interface color-scheme "$scheme" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface gtk-theme "$gtk_theme" 2>/dev/null || true
    elif command -v dconf >/dev/null 2>&1; then
        dconf write /org/gnome/desktop/interface/color-scheme "'$scheme'" 2>/dev/null || true
        dconf write /org/gnome/desktop/interface/gtk-theme "'$gtk_theme'" 2>/dev/null || true
    fi
}

# 5. Multi-Tier Theme Mode Resolution Pipeline
ACTION="${1:-}"

# Handle 'status' query
if [ "$ACTION" = "status" ]; then
    curr_scheme="unknown"
    if command -v gsettings >/dev/null 2>&1; then
        curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "unknown")
    fi
    noctalia_mode="unknown"
    if command -v noctalia >/dev/null 2>&1; then
        noctalia_mode=$(noctalia msg theme-mode-get 2>/dev/null || echo "unknown")
    fi
    echo "Current Scheme: $curr_scheme | Noctalia Mode: $noctalia_mode"
    exit 0
fi

# Handle 'toggle'
if [ "$ACTION" = "toggle" ]; then
    if command -v noctalia >/dev/null 2>&1 && noctalia msg status >/dev/null 2>&1; then
        noctalia msg theme-mode-toggle 2>/dev/null || true
        sleep 0.3
        TARGET_MODE=$(noctalia msg theme-mode-get 2>/dev/null || echo "")
        if [ "$TARGET_MODE" = "auto" ] || [ -z "$TARGET_MODE" ]; then
            TARGET_MODE="$DEFAULT_FALLBACK_MODE"
        fi
    else
        curr_scheme="prefer-dark"
        if command -v gsettings >/dev/null 2>&1; then
            curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "prefer-dark")
        fi
        if [ "$curr_scheme" = "prefer-dark" ]; then
            TARGET_MODE="light"
        else
            TARGET_MODE="dark"
        fi
    fi
elif [ "$ACTION" = "dark" ] || [ "$ACTION" = "light" ]; then
    TARGET_MODE="$ACTION"
    if command -v noctalia >/dev/null 2>&1 && noctalia msg status >/dev/null 2>&1; then
        noctalia msg theme-mode-set "$ACTION" 2>/dev/null || true
        sleep 0.2
    fi
else
    # Derived from hook environment, Noctalia IPC, or system query
    TARGET_MODE="${NOCTALIA_THEME_MODE:-}"
    if [ -z "$TARGET_MODE" ] && command -v noctalia >/dev/null 2>&1; then
        TARGET_MODE=$(noctalia msg theme-mode-get 2>/dev/null || echo "")
    fi
    if [ "$TARGET_MODE" = "auto" ] || [ -z "$TARGET_MODE" ]; then
        if command -v gsettings >/dev/null 2>&1; then
            curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "")
            if [ "$curr_scheme" = "prefer-light" ] || [ "$curr_scheme" = "default" ]; then
                TARGET_MODE="light"
            elif [ -n "$curr_scheme" ]; then
                TARGET_MODE="dark"
            else
                TARGET_MODE="$DEFAULT_FALLBACK_MODE"
            fi
        else
            TARGET_MODE="$DEFAULT_FALLBACK_MODE"
        fi
    fi
fi

# Normalize Target Parameters
if [ "$TARGET_MODE" = "light" ]; then
    SCHEME_VAL="prefer-light"
    GTK_THEME="$GTK_THEME_LIGHT"
    DARK_PREF="false"
    KVANTUM_THEME="$KVANTUM_THEME_LIGHT"
else
    SCHEME_VAL="prefer-dark"
    GTK_THEME="$GTK_THEME_DARK"
    DARK_PREF="true"
    KVANTUM_THEME="$KVANTUM_THEME_DARK"
fi

# 6. Broadcast to GSettings / XDG Desktop Portal
set_system_theme "$SCHEME_VAL" "$GTK_THEME"

# 7. Atomic Sync to GTK 3.0 & GTK 4.0 INI Files
atomic_update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-application-prefer-dark-theme" "$DARK_PREF"
atomic_update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-theme-name" "$GTK_THEME"
atomic_update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-application-prefer-dark-theme" "$DARK_PREF"
atomic_update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-theme-name" "$GTK_THEME"

# Clean up any legacy or stale GTK CSS overrides that break Libadwaita/Nautilus
for css_dir in "$HOME/.config/gtk-4.0" "$HOME/.config/gtk-3.0"; do
    if [ -f "$css_dir/noctalia.css" ]; then
        rm -f "$css_dir/noctalia.css" 2>/dev/null || true
    fi
    if [ -f "$css_dir/gtk.css" ] && grep -E -q "libadwaita\.css|noctalia\.css" "$css_dir/gtk.css" 2>/dev/null; then
        grep -v "libadwaita\.css\|noctalia\.css" "$css_dir/gtk.css" > "$css_dir/gtk.css.tmp" 2>/dev/null || true
        mv -f "$css_dir/gtk.css.tmp" "$css_dir/gtk.css" 2>/dev/null || true
    fi
done

# 8. Hot-Reload Running Applications Live
# Kitty terminal hot reload
if command -v pkill >/dev/null 2>&1; then
    pkill -SIGUSR1 -f "kitty" 2>/dev/null || true
fi

# Kvantum Qt theme synchronization (silent INI update only if theme directory exists)
if [ -d "/usr/share/Kvantum/$KVANTUM_THEME" ] || [ -d "$HOME/.config/Kvantum/$KVANTUM_THEME" ]; then
    atomic_update_ini "$HOME/.config/Kvantum/kvantum.kvconfig" "theme" "$KVANTUM_THEME"
fi

if command -v noctalia >/dev/null 2>&1; then
    GTK3_COLORS_DIR="$HOME/.config/gtk-3.0"
    GTK4_COLORS_DIR="$HOME/.config/gtk-4.0"
    PALETTE_CSS="noctalia-material-you.css"
    PALETTE_TMP="${XDG_RUNTIME_DIR:-/tmp}/noctalia-gtk-palette.css"

    noctalia msg palette-export --format gtk-css > "$PALETTE_TMP" 2>/dev/null || true

    if [ -s "$PALETTE_TMP" ]; then
        for css_dir in "$GTK3_COLORS_DIR" "$GTK4_COLORS_DIR"; do
            mkdir -p "$css_dir" 2>/dev/null || true
            cp -f "$PALETTE_TMP" "$css_dir/$PALETTE_CSS" 2>/dev/null || true
            if [ -f "$css_dir/gtk.css" ]; then
                if ! grep -q "$PALETTE_CSS" "$css_dir/gtk.css" 2>/dev/null; then
                    printf '\n@import url("%s");\n' "$PALETTE_CSS" >> "$css_dir/gtk.css"
                fi
            else
                printf '@import url("%s");\n' "$PALETTE_CSS" > "$css_dir/gtk.css"
            fi
        done
    fi
    rm -f "$PALETTE_TMP" 2>/dev/null || true
fi

# 9. Feedback for Interactive CLI Invocations
if [ -t 1 ] && [ -n "$ACTION" ]; then
    echo "Theme synced to: $TARGET_MODE (Scheme: $SCHEME_VAL, GTK: $GTK_THEME)"
fi
