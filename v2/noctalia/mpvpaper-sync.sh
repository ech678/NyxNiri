#!/bin/bash
# Hook to synchronize mpvpaper's video wallpaper with Noctalia's native wallpaper and theme.

# Check dependencies
for cmd in jq ffmpeg inotifywait noctalia; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: Required command '$cmd' is missing." >&2
        exit 1
    fi
done

ASSIGNMENTS_FILE="$HOME/.local/state/noctalia/mpvpaper/assignments.json"

process_assignments() {
    # Extract the first video path using jq
    if [ ! -f "$ASSIGNMENTS_FILE" ]; then
        return
    fi
    
    VIDEO_PATH=$(jq -r 'to_entries | .[0].value // empty' "$ASSIGNMENTS_FILE")
    
    if [[ -n "$VIDEO_PATH" && -f "$VIDEO_PATH" ]]; then
        # Check if it's a video
        if [[ "$VIDEO_PATH" == *.mp4 ]] || [[ "$VIDEO_PATH" == *.webm ]] || [[ "$VIDEO_PATH" == *.mkv ]] || [[ "$VIDEO_PATH" == *.mov ]] || [[ "$VIDEO_PATH" == *.gif ]]; then
            # Generate a hash-based filename for the thumbnail to avoid re-generating for the same video
            THUMB_NAME=$(echo -n "$VIDEO_PATH" | md5sum | awk '{print $1}')
            THUMB_PATH="$HOME/.cache/noctalia/mpvpaper/${THUMB_NAME}.jpg"
            
            mkdir -p "$(dirname "$THUMB_PATH")"
            
            # Generate thumbnail if it doesn't exist
            if [ ! -f "$THUMB_PATH" ]; then
                ffmpeg -y -i "$VIDEO_PATH" -ss 00:00:01 -vframes 1 "$THUMB_PATH" 2>/dev/null
            fi
            
            # Set it as the native Noctalia wallpaper
            CURRENT_WP=$(noctalia msg wallpaper-get 2>/dev/null)
            if [ "$CURRENT_WP" != "$THUMB_PATH" ]; then
                noctalia msg wallpaper-set "$THUMB_PATH"
            fi
        fi
    fi
}

# Ensure assignments file and directory exist so inotifywait doesn't fail immediately
mkdir -p "$(dirname "$ASSIGNMENTS_FILE")"
touch "$ASSIGNMENTS_FILE"

process_assignments

# Watch for changes
while inotifywait -q -e close_write "$ASSIGNMENTS_FILE"; do
    process_assignments
done
