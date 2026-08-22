#!/usr/bin/env bash

# ==============================================================================
# $PROJECT_NAME Configuration Backup, Snapshot, Rollback & Uninstall Manager
# ==============================================================================

set -euo pipefail

BACKUP_BASE_DIR="$HOME/.config/$PROJECT_NAME/backups"
declare -a CONFIG_ITEMS=()

discover_config_items() {
    CONFIG_ITEMS=()
    local repo_v2="${REPO_DIR:-.}/$CONFIG_DIR_NAME"
    if [ -d "$repo_v2" ]; then
        for entry in "$repo_v2"/*; do
            if [ -e "$entry" ]; then
                local base
                base=$(basename "$entry")
                CONFIG_ITEMS+=("$base")
            fi
        done
    fi
    if [ ${#CONFIG_ITEMS[@]} -eq 0 ]; then
        CONFIG_ITEMS=("fish" "noctalia" "niri" "kitty" "fastfetch" "starship.toml" "zed")
    fi
}

_stage_existing_configs() {
    local target_dir="$1"
    local log_msg_flag="${2:-0}"
    for item in "${CONFIG_ITEMS[@]}"; do
        if [ -e "$HOME/.config/$item" ]; then
            cp -rP "$HOME/.config/$item" "$target_dir/"
            if [ "$log_msg_flag" = "1" ]; then
                msg log_backup_item "$item"
            fi
        fi
    done
    return 0
}

backup_configs() {
    local note="${1:-}"

    msg backing_up
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/snapshot_$timestamp"

    local tmp_snap
    tmp_snap=$(mktemp -d) || return 1
    register_temp_path "$tmp_snap"

    _stage_existing_configs "$tmp_snap" 1

    if [ -n "$note" ]; then
        echo "$note" > "$tmp_snap/note.txt"
    fi

    mkdir -p "$BACKUP_BASE_DIR"
    mv "$tmp_snap" "$backup_dir"

    msg backup_done "$backup_dir"
}

declare -a ALL_BACKUPS=()
get_all_backups() {
    ALL_BACKUPS=()
    local -a raw=()
    if [ -d "$BACKUP_BASE_DIR" ]; then
        for d in "$BACKUP_BASE_DIR"/*; do
            [ -d "$d" ] && raw+=("$d")
        done
    fi
    # Backward-compatible legacy backup dirs left in ~/.config by older versions.
    for d in "$HOME/.config"/dotfiles_backup_*; do
        [ -d "$d" ] && raw+=("$d")
    done
    if [ ${#raw[@]} -gt 0 ]; then
        # ISO timestamps sort lexicographically = chronologically.
        mapfile -t ALL_BACKUPS < <(printf '%s\n' "${raw[@]}" | sort)
    fi
}

list_backups() {
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    msg available_backups
    local idx=1
    for b in "${ALL_BACKUPS[@]}"; do
        if [ -d "$b" ]; then
            local bname
            bname=$(basename "$b")
            local note=""
            if [ -f "$b/note.txt" ]; then
                note=" ($(head -n1 "$b/note.txt" 2>/dev/null || echo ""))"
            fi
            echo -e "  \e[1;32m[$idx]\e[0m $bname$note"
            idx=$((idx + 1))
        fi
    done
    return 0
}

rollback_configs() {
    local target_idx="${1:-}"
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    local valid_backups=()
    for b in "${ALL_BACKUPS[@]}"; do
        if [ -d "$b" ]; then
            valid_backups+=("$b")
        fi
    done

    if [ -z "$target_idx" ]; then
        list_backups
        echo ""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -r -p "$(msg select_rollback_target)" target_idx < /dev/tty || target_idx=""
        fi
    fi

    if [[ ! "$target_idx" =~ ^[0-9]+$ ]] || [ "$target_idx" -lt 1 ] || [ "$target_idx" -gt "${#valid_backups[@]}" ]; then
        msg rollback_invalid_num
        return 1
    fi

    local selected_backup="${valid_backups[$((target_idx-1))]}"
    local selected_bname
    selected_bname=$(basename "$selected_backup")

    # Safety auto-backup before rollback
    local pre_ts
    pre_ts=$(date +%Y%m%d_%H%M%S)
    local pre_dir="$BACKUP_BASE_DIR/pre_rollback_$pre_ts"
    local pre_tmp
    pre_tmp=$(mktemp -d) || return 1
    register_temp_path "$pre_tmp"
    _stage_existing_configs "$pre_tmp" 0
    echo "pre-rollback safety snapshot" > "$pre_tmp/note.txt"
    mkdir -p "$BACKUP_BASE_DIR"
    mv "$pre_tmp" "$pre_dir"
    msg pre_rollback_backup "$pre_dir"

    msg rolling_back "$selected_bname"
    for item in "${CONFIG_ITEMS[@]}"; do
        if [ -e "$selected_backup/$item" ]; then
            atomic_replace_dir "$selected_backup/$item" "$HOME/.config/$item"
            msg log_restore_item "$item"
        fi
    done

    msg rollback_done "$selected_bname"
}

# Delete a single snapshot (by index, or interactive selection). The oldest
# snapshot may hold the pre-install state that "uninstall --restore" depends
# on, so deletion always requires explicit confirmation.
delete_backup() {
    local target_idx="${1:-}"
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    local valid_backups=()
    for b in "${ALL_BACKUPS[@]}"; do
        [ -d "$b" ] && valid_backups+=("$b")
    done

    if [ -z "$target_idx" ]; then
        list_backups
        echo ""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -r -p "$(msg select_rollback_target)" target_idx < /dev/tty || target_idx=""
        fi
    fi

    if [[ ! "$target_idx" =~ ^[0-9]+$ ]] || [ "$target_idx" -lt 1 ] || [ "$target_idx" -gt "${#valid_backups[@]}" ]; then
        msg delete_invalid_num
        return 1
    fi

    local selected="${valid_backups[$((target_idx-1))]}"
    local selected_name
    selected_name=$(basename "$selected")

    msg delete_confirm "$selected_name"
    local confirm=""
    if [ -t 0 ] && [ -c /dev/tty ]; then
        read -r -p "$(msg delete_prompt)" confirm < /dev/tty || confirm="n"
    fi
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        msg delete_cancelled
        return 0
    fi

    rm -rf "$selected" 2>/dev/null || true
    msg delete_done "$selected_name" "$(( ${#valid_backups[@]} - 1 ))"
}

uninstall_nyxniri() {
    local mode="${1:-}"
    if [ -z "$mode" ]; then
        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            return 0
        fi

        local cur_focus=0
        clear 2>/dev/null || true

        while true; do
            printf '\e[?25l\e[H'
            show_logo
            msg uninstall_title

            _render_menu_item 0 "$(msg uninstall_opt1)" "$cur_focus"
            _render_menu_item 1 "$(msg uninstall_opt2)" "$cur_focus"
            _render_menu_item 2 "$(msg uninstall_opt3)" "$cur_focus" "warn"
            _render_menu_item 3 "$(msg uninstall_opt4)" "$cur_focus" "subtle"

            echo ""
            msg submenu_hint
            echo ""
            printf '\e[J'

            local key
            key=$(read_key) || return 0
            handle_menu_key "$key" "$cur_focus" 3
            cur_focus="$_MENU_FOCUS"

            if [ "$_MENU_ACTION" -ne -1 ]; then
                printf '\e[?25h'
                mode=$((_MENU_ACTION + 1))
                break
            fi
        done
        printf '\e[?25h'
    fi

    case "$mode" in
        1|safe|--safe)
            local ts
            ts=$(date +%Y%m%d_%H%M%S)
            local archive_file="$HOME/.config/NyxNiri_final_backup_$ts.tar.gz"
            local temp_stage
            temp_stage=$(mktemp -d) || return 1
            register_temp_path "$temp_stage"
            _stage_existing_configs "$temp_stage" 0
            tar -czf "$archive_file" -C "$temp_stage" . 2>/dev/null || true
            rm -rf "$temp_stage" 2>/dev/null || true
            msg uninstall_archived "$archive_file"

            for item in "${CONFIG_ITEMS[@]}"; do
                if [ -e "$HOME/.config/$item" ] && [ "$HOME/.config/$item" != "$HOME" ]; then
                    rm -rf "$HOME/.config/$item"
                    msg log_remove_item "$item"
                fi
            done
            [ -L "$HOME/.local/bin/$CLI_CMD" ] && rm -f "$HOME/.local/bin/$CLI_CMD"
            fcitx_uninstall || true
            msg uninstall_done
            ;;
        2|restore|--restore)
            get_all_backups
            if [ ${#ALL_BACKUPS[@]} -gt 0 ] && [ -n "${ALL_BACKUPS[0]:-}" ] && [ -d "${ALL_BACKUPS[0]}" ]; then
                local earliest="${ALL_BACKUPS[0]}"
                local earliest_name
                earliest_name=$(basename "$earliest")
                msg log_restoring_origin_config "$earliest_name"
                for item in "${CONFIG_ITEMS[@]}"; do
                    if [ -e "$earliest/$item" ]; then
                        atomic_replace_dir "$earliest/$item" "$HOME/.config/$item"
                        msg log_restore_item "$item"
                    fi
                done
                [ -L "$HOME/.local/bin/$CLI_CMD" ] && rm -f "$HOME/.local/bin/$CLI_CMD"
                msg restore_origin_done
            else
                msg no_backups_found
            fi
            ;;
        3|purge|--purge)
            for item in "${CONFIG_ITEMS[@]}"; do
                if [ -e "$HOME/.config/$item" ] && [ "$HOME/.config/$item" != "$HOME" ]; then
                    rm -rf "$HOME/.config/$item"
                fi
            done
            [ -L "$HOME/.local/bin/$CLI_CMD" ] && rm -f "$HOME/.local/bin/$CLI_CMD"
            [ -d "$HOME/.cache/$PROJECT_NAME" ] && rm -rf "$HOME/.cache/$PROJECT_NAME"
            [ -d "$HOME/.config/$PROJECT_NAME" ] && rm -rf "$HOME/.config/$PROJECT_NAME"
            fcitx_uninstall || true
            local pics_dir
            pics_dir="$(get_pics_dir)"
            [ -d "$pics_dir/Wallpapers" ] && rm -rf "$pics_dir/Wallpapers"
            msg purge_done
            ;;
        *)
            msg log_uninstall_cancelled
            return 0
            ;;
    esac
}
