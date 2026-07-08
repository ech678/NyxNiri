#!/bin/bash

# Get current theme mode (from env, or fallback to CLI)
THEME_MODE="${NOCTALIA_THEME_MODE}"
if [ -z "$THEME_MODE" ]; then
    THEME_MODE=$(noctalia msg theme-mode-get 2>/dev/null || echo "dark")
fi

echo "Syncing theme mode to: $THEME_MODE"

# Function to update settings in INI files safely
update_ini() {
    local file="$1"
    local key="$2"
    local val="$3"
    
    if [ ! -f "$file" ]; then
        return
    fi
    
    if grep -q "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$file"
    else
        # Append right after the [Settings] section line
        if grep -q "^\[Settings\]" "$file"; then
            sed -i "/^\[Settings\]/a ${key}=${val}" "$file"
        else
            echo "${key}=${val}" >> "$file"
        fi
    fi
}

if [ "$THEME_MODE" = "light" ]; then
    # 1. Update GSettings (affects Firefox, Chromium, VS Code, and libadwaita apps)
    gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
    gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3'
    
    # 2. Update GTK 3.0 settings.ini
    update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-application-prefer-dark-theme" "false"
    update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-theme-name" "adw-gtk3"
    
    # 3. Update GTK 4.0 settings.ini
    update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-application-prefer-dark-theme" "false"
else
    # 1. Update GSettings
    gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
    gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3-dark'
    
    # 2. Update GTK 3.0 settings.ini
    update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-application-prefer-dark-theme" "true"
    update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-theme-name" "adw-gtk3-dark"
    
    # 3. Update GTK 4.0 settings.ini
    update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-application-prefer-dark-theme" "true"
fi
