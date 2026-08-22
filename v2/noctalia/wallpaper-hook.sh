#!/bin/bash
set -uo pipefail

# Ensure noctalia is available
if ! command -v noctalia >/dev/null 2>&1; then
    exit 1
fi

WP=$(noctalia msg wallpaper-get 2>/dev/null)

# Define user-specific log path
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/noctalia"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/hook.log"

echo "$(date) wallpaper_changed hook triggered. WP=$WP" >> "$LOG_FILE"

# Only process video files to avoid infinite loops
if [[ -n "$WP" && -f "$WP" && "$WP" =~ \.(mp4|webm|mkv|mov|gif)$ ]]; then
    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "Error: ffmpeg is not installed." >> "$LOG_FILE"
        exit 1
    fi

    echo "Video detected, generating thumbnail and setting it as wallpaper..." >> "$LOG_FILE"
    
    # Define user-specific thumbnail path in a secure/private location
    THUMB_DIR="${XDG_RUNTIME_DIR:-/tmp/noctalia-$USER}"
    mkdir -p "$THUMB_DIR"
    THUMB_PATH="$THUMB_DIR/mpvpaper_thumb.jpg"
    
    # Generate thumbnail
    if ffmpeg -y -i "$WP" -ss 00:00:01 -vframes 1 "$THUMB_PATH" 2>/dev/null; then
        # Set the thumbnail as wallpaper to extract colors and provide a static background
        noctalia msg wallpaper-set "$THUMB_PATH" 2>/dev/null || true
    else
        echo "Error: ffmpeg failed to extract thumbnail from $WP" >> "$LOG_FILE"
    fi
fi
