#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Optional Module — NyxMellow Dynamic Fcitx5 Skin (Noctalia template)
# Deploys the mellow-shaped fcitx5 theme templates and registers them as
# Noctalia user templates so colors follow the Material You palette, then
# switches fcitx5 to the rendered theme. All steps are failure-tolerant.
# ==============================================================================

set -euo pipefail

FCITX_THEMES_DIR="$HOME/.local/share/fcitx5/themes"
FCITX_THEME_DIR="$FCITX_THEMES_DIR/$FCITX_THEME"
FCITX_TEMPLATE_DIR="$FCITX_THEME_DIR/templates"
FCITX_CLASSICUI_CONF="$HOME/.config/fcitx5/conf/classicui.conf"
FCITX_NOCTALIA_CONFIG="$HOME/.config/$THEME_ENGINE/$THEME_ENGINE-config.toml"
FCITX_STATE_FILE="$HOME/.local/state/$PROJECT_NAME/fcitx-$FCITX_THEME-theme.prev"
# Consent marker: touched only when the user explicitly opts into the skin
# (via `$CLI_CMD fcitx install` or an install/update consent prompt). Automation
# (non-interactive deploys) refreshes the skin only when this marker exists.
FCITX_ENABLED_MARKER="$HOME/.local/state/$PROJECT_NAME/fcitx-$FCITX_THEME.enabled"
FCITX_TEMPLATE_PREFIX="theme.templates.user.${FCITX_THEME}_"

# Resolve the repo source dir at call time: REPO_DIR is set by
# init_environment_paths *after* this module is sourced, so it must not be
# expanded here (would wrongly fall back to "." / the current working dir).
fcitx_source_dir() {
    echo "${REPO_DIR:-.}/fcitx5/$FCITX_THEME/templates"
}

fcitx5_installed() {
    command -v fcitx5 >/dev/null 2>&1
}

noctalia_available() {
    command -v "$THEME_ENGINE" >/dev/null 2>&1
}

# Compact status label for menus (bilingual via i18n).
fcitx_status_label() {
    if ! fcitx5_installed; then
        msg status_fcitx5_missing
    elif fcitx_enabled; then
        msg status_enabled
    else
        msg status_disabled
    fi
}

fcitx_enabled() {
    [ -f "$FCITX_ENABLED_MARKER" ]
}

# Consent gate for applying/refreshing the NyxMellow skin. Always asks when
# fcitx5 is installed (updates may ship skin changes); non-interactive only
# auto-refreshes when the user previously opted in (marker present). Returns
# 0 to apply, 1 to skip.
fcitx_consent_ask() {
    if ! fcitx5_installed; then
        msg fcitx_skipped_not_installed
        return 1
    fi
    fcitx_enabled
    return $?
}

fcitx_templates_registered() {
    [ -f "$FCITX_NOCTALIA_CONFIG" ] && grep -q "^\[${FCITX_TEMPLATE_PREFIX}" "$FCITX_NOCTALIA_CONFIG" 2>/dev/null
}

# Remember the pre-existing Theme/DarkTheme once, so uninstall can restore them.
fcitx_backup_theme_settings() {
    mkdir -p "$(dirname "$FCITX_STATE_FILE")"
    [ -f "$FCITX_STATE_FILE" ] && return 0
    local existed=0 t="" dt=""
    if [ -f "$FCITX_CLASSICUI_CONF" ]; then
        existed=1
        t=$(grep -m1 '^Theme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
    fi
    printf 'Existed=%s\nTheme=%s\nDarkTheme=%s\n' "$existed" "$t" "$dt" > "$FCITX_STATE_FILE"
}

fcitx_deploy_templates() {
    local src_dir
    src_dir="$(fcitx_source_dir)"
    if [ ! -d "$src_dir" ]; then
        msg log_fcitx_template_missing "$src_dir"
        return 1
    fi
    mkdir -p "$FCITX_TEMPLATE_DIR"
    cp -a "$src_dir"/. "$FCITX_TEMPLATE_DIR"/ 2>/dev/null || cp -a "$src_dir" "$FCITX_TEMPLATE_DIR"/
    msg fcitx_templates_deployed
}

# Targeted update of classicui.conf (only touches Theme/DarkTheme).
fcitx_update_conf() {
    local key="$1" val="$2"
    local esc_val
    esc_val=$(printf '%s\n' "$val" | sed 's/[|&]/\\&/g')
    if [ -f "$FCITX_CLASSICUI_CONF" ] && grep -q "^${key}=" "$FCITX_CLASSICUI_CONF"; then
        sed -i "s|^${key}=.*|${key}=${esc_val}|" "$FCITX_CLASSICUI_CONF"
    else
        mkdir -p "$(dirname "$FCITX_CLASSICUI_CONF")"
        echo "${key}=${val}" >> "$FCITX_CLASSICUI_CONF"
    fi
}

fcitx_set_theme_conf() {
    fcitx_backup_theme_settings
    fcitx_update_conf "Theme" "$FCITX_THEME"
    fcitx_update_conf "DarkTheme" "$FCITX_THEME"
    msg fcitx_theme_set "$FCITX_CLASSICUI_CONF"
}

fcitx_restart() {
    if fcitx5_installed && pgrep -x fcitx5 >/dev/null 2>&1; then
        pkill -x fcitx5 2>/dev/null || true
        sleep 1
        fcitx5 -d >/dev/null 2>&1 || true
        msg fcitx_restarted
    fi
}

# Ask $THEME_ENGINE to render the user templates for the current palette.
# config-reload first so a freshly deployed registration is picked up, then
# templates-apply renders unconditionally (unlike config-reload, which is a
# no-op when nothing changed).
fcitx_trigger_render() {
    if noctalia_available; then
        "$THEME_ENGINE" msg config-reload >/dev/null 2>&1 || true
        if "$THEME_ENGINE" msg templates-apply >/dev/null 2>&1; then
            msg fcitx_render_ok
        else
            msg fcitx_render_pending
        fi
    else
        msg fcitx_render_pending
    fi
}

# Safely set a key=val pair under a specific [section] in an INI file without corrupting existing sections.
fcitx_update_ini_setting() {
    local file="$1" section="$2" key="$3" val="$4"
    local esc_val
    esc_val=$(printf '%s\n' "$val" | sed 's/[|&]/\\&/g')
    if [ ! -f "$file" ]; then
        mkdir -p "$(dirname "$file")"
        printf '[%s]\n%s=%s\n' "$section" "$key" "$val" > "$file"
        return 0
    fi

    if grep -q "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${esc_val}|" "$file"
    else
        if grep -q "^\[${section}\]" "$file"; then
            sed -i "/^\[${section}\]/a ${key}=${esc_val}" "$file"
        else
            printf '\n[%s]\n%s=%s\n' "$section" "$key" "$val" >> "$file"
        fi
    fi
}

fcitx_configure_quickphrase() {
    local qp_conf="$HOME/.config/fcitx5/conf/quickphrase.conf"
    fcitx_update_ini_setting "$qp_conf" "Hotkey" "TriggerKey" "Super+semicolon"
    fcitx_update_ini_setting "$qp_conf" "Hotkey" "AlternativeTriggerKey" ""
}

fcitx_install() {
    msg fcitx_install_title
    if ! fcitx_deploy_templates; then
        return 1
    fi
    if fcitx5_installed; then
        fcitx_set_theme_conf
        fcitx_configure_quickphrase
        fcitx_trigger_render
        fcitx_restart
        mkdir -p "$(dirname "$FCITX_ENABLED_MARKER")"
        touch "$FCITX_ENABLED_MARKER"
    else
        msg fcitx_skip_no_fcitx5
    fi
}

# Failure-tolerant entry used by the update flow (never aborts set -e).
# Consent-gated: never auto-enables an unregistered skin. fcitx5 must be
# present; interactive runs always re-ask, since updates may ship skin changes.
deploy_fcitx_theme() {
    if fcitx_consent_ask; then
        fcitx_install || true
    fi
}

fcitx_status() {
    msg fcitx_status_title

    if fcitx5_installed; then
        msg doctor_ok "fcitx5: installed"
    else
        msg doctor_warn "fcitx5: not installed"
    fi

    if fcitx_templates_registered; then
        msg fcitx_registered "$FCITX_NOCTALIA_CONFIG"
    else
        msg fcitx_not_registered "$FCITX_NOCTALIA_CONFIG"
    fi

    if [ -d "$FCITX_THEME_DIR" ]; then
        msg doctor_ok "theme dir: $FCITX_THEME_DIR"
        if [ -f "$FCITX_THEME_DIR/theme.conf" ] && [ -f "$FCITX_THEME_DIR/panel.svg" ] && [ -f "$FCITX_THEME_DIR/highlight.svg" ]; then
            msg doctor_ok "rendered files: present (follows Noctalia colors)"
        else
            msg doctor_warn "rendered files: missing — run $THEME_ENGINE msg config-reload or $CLI_CMD fcitx install"
        fi
    else
        msg doctor_warn "theme dir: $FCITX_THEME_DIR missing"
    fi

    if [ -f "$FCITX_CLASSICUI_CONF" ]; then
        local t="" dt=""
        t=$(grep -m1 '^Theme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_CLASSICUI_CONF" 2>/dev/null | cut -d= -f2- || true)
        msg doctor_ok "classicui.conf: Theme=$t DarkTheme=$dt"
    else
        msg doctor_warn "classicui.conf: missing"
    fi
}

fcitx_uninstall() {
    msg fcitx_uninstall_title

    if fcitx_templates_registered; then
        awk -v prefix="$FCITX_TEMPLATE_PREFIX" '
            $0 ~ ("^\\[" prefix) { skip = 1; next }
            skip && /^\[/ { skip = 0 }
            skip { next }
            { print }
        ' "$FCITX_NOCTALIA_CONFIG" > "$FCITX_NOCTALIA_CONFIG.tmp" && mv "$FCITX_NOCTALIA_CONFIG.tmp" "$FCITX_NOCTALIA_CONFIG"
        msg log_fcitx_template_unregistered "$THEME_ENGINE"
    fi

    if [ -d "$FCITX_THEME_DIR" ]; then
        rm -rf "$FCITX_THEME_DIR"
        msg log_fcitx_theme_dir_removed "$FCITX_THEME_DIR"
    fi

    if [ -f "$FCITX_STATE_FILE" ]; then
        local existed t dt
        existed=$(grep -m1 '^Existed=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        t=$(grep -m1 '^Theme=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        dt=$(grep -m1 '^DarkTheme=' "$FCITX_STATE_FILE" 2>/dev/null | cut -d= -f2- || true)
        if [ "$existed" != "1" ]; then
            rm -f "$FCITX_CLASSICUI_CONF"
        else
            if [ -n "$t" ]; then
                fcitx_update_conf "Theme" "$t"
            else
                sed -i '/^Theme=/d' "$FCITX_CLASSICUI_CONF" 2>/dev/null || true
            fi
            if [ -n "$dt" ]; then
                fcitx_update_conf "DarkTheme" "$dt"
            else
                sed -i '/^DarkTheme=/d' "$FCITX_CLASSICUI_CONF" 2>/dev/null || true
            fi
        fi
        rm -f "$FCITX_STATE_FILE"
    fi

    rm -f "$FCITX_ENABLED_MARKER" 2>/dev/null || true

    fcitx_restart
    msg fcitx_uninstall_done
}

fcitx_usage() {
    echo "Usage: $CLI_CMD fcitx [install|uninstall|status]"
    echo ""
    echo "  install     Deploy theme templates, register $THEME_ENGINE templates, switch fcitx5 to $FCITX_THEME"
    echo "  uninstall   Restore previous fcitx5 config, unregister from $THEME_ENGINE, clear state"
    echo "  status      Check fcitx5 daemon, theme registration, and rendered files"
}
