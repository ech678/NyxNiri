#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Optional Module — Noctalia Greeter (greetd Login)
# Dedicated module for the optional login greeter dependency and its system
# configuration. All privileged steps run via sudo (never as root) and are
# failure-tolerant: a failed privileged step only logs a warning and the main
# flow continues, reporting a summary at the end.
# ==============================================================================

set -euo pipefail

GREETER_SESSION_BIN="noctalia-greeter-session"
GREETER_ETC_CFG="/etc/greetd/config.toml"
GREETER_STATE_DIR="/var/lib/$GREETER_PKG"
GREETER_POLKIT_RULE="/etc/polkit-1/rules.d/50-$GREETER_PKG.rules"
GREETER_CONFLICT_DMS=(sddm lightdm gdm ly)

greeter_installed() {
    command -v "$GREETER_SESSION_BIN" >/dev/null 2>&1
}

# Compact status label for menus (bilingual via i18n).
greeter_status_label() {
    if ! greeter_installed; then
        msg status_not_installed
        return 0
    fi
    local cfg_ok=false
    if [ -f "$GREETER_ETC_CFG" ] && grep -q "$GREETER_SESSION_BIN" "$GREETER_ETC_CFG" 2>/dev/null; then
        cfg_ok=true
    fi
    if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled greetd >/dev/null 2>&1 && [ "$cfg_ok" = "true" ]; then
        msg status_installed_enabled
    else
        msg status_installed
    fi
}

greeter_session_path() {
    if command -v "$GREETER_SESSION_BIN" >/dev/null 2>&1; then
        command -v "$GREETER_SESSION_BIN"
    else
        echo "/usr/bin/$GREETER_SESSION_BIN"
    fi
}

greeter_session_arg() {
    local arg=""
    if command -v "$GREETER_PKG" >/dev/null 2>&1; then
        if "$GREETER_PKG" sessions 2>/dev/null | grep -ixq "$MAIN_WM"; then
            arg="-- --session $MAIN_WM"
        fi
    fi
    echo "$arg"
}

greeter_greetd_missing() {
    command -v pacman >/dev/null 2>&1 && ! pacman -Qq greetd >/dev/null 2>&1
}

# /etc/polkit-1/rules.d is mode 750 root:polkitd on polkit 126+; a normal user
# cannot stat files inside it. Detect any *.rules file that grants the greeter
# action (content-based, so pre-existing rules under any filename count).
greeter_rule_visible() {
    [ -x "$(dirname "$GREETER_POLKIT_RULE")" ]
}

greeter_rule_present() {
    local rule_dir
    rule_dir="$(dirname "$GREETER_POLKIT_RULE")"
    if greeter_rule_visible; then
        grep -qs "org.${THEME_ENGINE}.greeter.apply-appearance" "$rule_dir"/*.rules 2>/dev/null
    else
        sudo -n sh -c "grep -qs 'org.${THEME_ENGINE}.greeter.apply-appearance' \"\$1\"/*.rules 2>/dev/null" sh "$rule_dir" 2>/dev/null
    fi
}

greeter_install_packages() {
    msg greeter_install_pkgs
    local pkg_manager
    pkg_manager=$(get_preferred_pkg_manager)
    local has_aur=false
    [ "$pkg_manager" != "sudo pacman" ] && has_aur=true

    if greeter_greetd_missing; then
        $pkg_manager -S --noconfirm greetd || msg greeter_pkg_failed "greetd"
    fi

    if ! greeter_installed; then
        local greeter_repo_installed=false
        if command -v pacman >/dev/null 2>&1; then
            pacman -Qq "$GREETER_PKG" >/dev/null 2>&1 && greeter_repo_installed=true
            pacman -Qq "$GREETER_PKG-git" >/dev/null 2>&1 && greeter_repo_installed=true
        fi
        if [ "$greeter_repo_installed" = false ]; then
            if [ "$has_aur" = true ]; then
                $pkg_manager -S --noconfirm "$GREETER_PKG" || msg greeter_pkg_failed "$GREETER_PKG"
            else
                msg greeter_aur_required
            fi
        fi
    fi

    if greeter_greetd_missing || ! greeter_installed; then
        msg greeter_install_failed
        return 1
    fi
    return 0
}

greeter_detect_dm_conflict() {
    command -v systemctl >/dev/null 2>&1 || return 0
    local found=() dm=""
    for dm in "${GREETER_CONFLICT_DMS[@]}"; do
        if systemctl is-enabled "$dm" >/dev/null 2>&1 && [ "$(systemctl is-enabled "$dm" 2>/dev/null)" != "disabled" ]; then
            found+=("$dm")
        fi
    done
    if [ ${#found[@]} -gt 0 ]; then
        msg greeter_dm_conflict "${found[*]}"
    fi
}

greeter_apply_greetd_config() {
    local session_path="$1" session_arg="$2"

    if [ -f "$GREETER_ETC_CFG" ] && grep -q "$GREETER_SESSION_BIN" "$GREETER_ETC_CFG" 2>/dev/null; then
        msg greeter_install_skipped
        return 0
    fi

    # Backup existing
    bak="${GREETER_ETC_CFG}.$CLI_CMD.bak.$(date +%Y%m%d_%H%M%S)"
    if [ -f "$GREETER_ETC_CFG" ]; then
        sudo cp -a "$GREETER_ETC_CFG" "$bak" 2>/dev/null || true
    fi

    local tmp_cfg
    tmp_cfg=$(mktemp) || return 0
    register_temp_path "$tmp_cfg"
    {
        echo "[terminal]"
        echo "vt = 1"
        echo ""
        echo "[default_session]"
        local cmd_line="$session_path"
        if [ -n "$session_arg" ]; then
            cmd_line="$cmd_line $session_arg"
        fi
        echo "command = \"$cmd_line\""
        echo "user = \"greeter\""
    } > "$tmp_cfg"

    if sudo mkdir -p /etc/greetd 2>/dev/null && sudo install -m 0644 -o root -g root "$tmp_cfg" "$GREETER_ETC_CFG" 2>/dev/null; then
        msg greeter_config_written "$GREETER_ETC_CFG"
    else
        msg greeter_config_failed "$GREETER_ETC_CFG"
    fi
}

greeter_ensure_state_dir() {
    if [ ! -d "$GREETER_STATE_DIR" ]; then
        if sudo mkdir -p "$GREETER_STATE_DIR" 2>/dev/null; then
            sudo chown greeter:greeter "$GREETER_STATE_DIR" 2>/dev/null || true
            msg greeter_state_dir_created
        else
            msg greeter_cmd_failed "mkdir $GREETER_STATE_DIR"
        fi
    fi
}

greeter_apply_polkit_rule() {
    if greeter_rule_present; then
        msg greeter_polkit_skip
        return 0
    fi

    local tmp_rule
    tmp_rule=$(mktemp) || return 0
    register_temp_path "$tmp_rule"
    cat > "$tmp_rule" <<EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.${THEME_ENGINE}.greeter.apply-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF

    if sudo mkdir -p /etc/polkit-1/rules.d 2>/dev/null && sudo install -m 0644 -o root -g root "$tmp_rule" "$GREETER_POLKIT_RULE" 2>/dev/null; then
        msg greeter_polkit_written "$GREETER_POLKIT_RULE"
    else
        msg greeter_polkit_failed
    fi
}

greeter_enable_service() {
    command -v systemctl >/dev/null 2>&1 || { msg greeter_cmd_failed "systemctl"; return 0; }
    if systemctl is-enabled greetd >/dev/null 2>&1; then
        msg greeter_enabled_skip
        return 0
    fi
    if sudo systemctl enable greetd 2>/dev/null; then
        msg greeter_enabled
    else
        msg greeter_enable_failed
    fi
}

greeter_install() {
    msg greeter_install_title

    if ! greeter_installed || greeter_greetd_missing; then
        greeter_install_packages || return 1
    fi

    local session_path session_arg
    session_path=$(greeter_session_path)
    session_arg=$(greeter_session_arg)

    greeter_detect_dm_conflict
    greeter_apply_greetd_config "$session_path" "$session_arg"
    greeter_ensure_state_dir
    greeter_apply_polkit_rule
    greeter_enable_service

    msg greeter_reboot_hint
}

greeter_status() {
    msg greeter_status_title
    local err=0

    if command -v pacman >/dev/null 2>&1 && pacman -Qq greetd >/dev/null 2>&1; then
        msg doctor_ok "greetd: installed"
    else
        msg doctor_err "greetd: not installed"
        err=1
    fi

    if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled greetd >/dev/null 2>&1; then
        msg doctor_ok "greetd: service enabled"
    else
        msg doctor_warn "greetd: service not enabled"
    fi

    if greeter_installed; then
        msg doctor_ok "$GREETER_PKG: installed ($(greeter_session_path))"
    else
        msg doctor_err "$GREETER_PKG: not installed"
        err=1
    fi

    if [ -f "$GREETER_ETC_CFG" ]; then
        if grep -q "$GREETER_SESSION_BIN" "$GREETER_ETC_CFG" 2>/dev/null; then
            msg doctor_ok "greetd config: uses $GREETER_PKG"
        else
            msg doctor_warn "greetd config: not pointed at $GREETER_PKG"
        fi
    else
        msg doctor_warn "greetd config: $GREETER_ETC_CFG missing"
    fi

    if greeter_rule_present; then
        msg doctor_ok "polkit rule: present"
    elif greeter_rule_visible || sudo -n true 2>/dev/null; then
        msg doctor_warn "polkit rule: missing"
    else
        msg doctor_warn "polkit rule: unverifiable"
    fi

    if [ -d "$GREETER_STATE_DIR" ]; then
        msg doctor_ok "state dir: $GREETER_STATE_DIR"
    else
        msg doctor_warn "state dir: $GREETER_STATE_DIR missing"
    fi

    if [ -f "/usr/share/wayland-sessions/$MAIN_WM.desktop" ]; then
        msg doctor_ok "session: niri.desktop registered"
    else
        msg doctor_err "session: /usr/share/wayland-sessions/niri.desktop missing"
        err=1
    fi

    if [ "$err" -eq 0 ]; then
        msg greeter_status_ok
    else
        msg greeter_status_hint
    fi
}

greeter_uninstall() {
    msg greeter_uninstall_title

    if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled greetd >/dev/null 2>&1; then
        sudo systemctl disable greetd 2>/dev/null || msg greeter_cmd_failed "systemctl disable greetd"
    fi

    local bak
    bak=$(find "$(dirname "$GREETER_ETC_CFG")" -maxdepth 1 -name "$(basename "$GREETER_ETC_CFG").$CLI_CMD.bak.*" 2>/dev/null | sort | tail -n 1 || true)
    if [ -n "$bak" ] && [ -f "$bak" ]; then
        if sudo cp -a "$bak" "$GREETER_ETC_CFG" 2>/dev/null; then
            msg greeter_uninstall_restored "$bak"
        else
            msg greeter_cmd_failed "restore $GREETER_ETC_CFG"
        fi
    else
        msg greeter_uninstall_nobackup
    fi

    if [ -f "$GREETER_POLKIT_RULE" ]; then
        if sudo rm -f "$GREETER_POLKIT_RULE" 2>/dev/null; then
            msg greeter_uninstall_polkit
        else
            msg greeter_cmd_failed "rm $GREETER_POLKIT_RULE"
        fi
    fi

    msg greeter_uninstall_done
}
