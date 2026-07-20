#!/bin/bash

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
if [[ "$WP" == *.mp4 ]] || [[ "$WP" == *.webm ]] || [[ "$WP" == *.mkv ]] || [[ "$WP" == *.mov ]] || [[ "$WP" == *.gif ]]; then
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
    ffmpeg -y -i "$WP" -ss 00:00:01 -vframes 1 "$THUMB_PATH" 2>/dev/null
    
    # Set the thumbnail as wallpaper to extract colors and provide a static background
    noctalia msg wallpaper-set "$THUMB_PATH" 2>/dev/null
fi
