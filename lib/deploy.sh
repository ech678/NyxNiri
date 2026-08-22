#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Dotfiles Atomic Deployment & Hardware Configuration Engine
# ==============================================================================

set -euo pipefail

# Replace dest with a copy of src without ever leaving dest half-deleted:
# copy to a sibling temp dir first (dest untouched if this fails), then swap
# in with rm+mv instead of a long-running rm+cp that a Ctrl+C/crash could
# interrupt mid-copy.
atomic_replace_item() {
    local src="$1" dest="$2"
    if [ -f "$src" ]; then
        local tmp_file="${dest}.new.$$"
        rm -f "$tmp_file" 2>/dev/null || true
        register_temp_path "$tmp_file"
        cp -a "$src" "$tmp_file" || { rm -f "$tmp_file" 2>/dev/null || true; return 1; }
        if [ -e "$dest" ]; then
            local old_dest="${dest}.old.$$"
            mv "$dest" "$old_dest" || return 1
            mv "$tmp_file" "$dest" || { mv "$old_dest" "$dest"; return 1; }
            ( rm -f "$old_dest" & ) 2>/dev/null
        else
            mv "$tmp_file" "$dest"
        fi
        return 0
    fi

    local tmp_new="${dest}.new.$$"
    rm -rf "$tmp_new" 2>/dev/null || true
    register_temp_path "$tmp_new"
    cp -a "$src" "$tmp_new" || { rm -rf "$tmp_new" 2>/dev/null || true; return 1; }

    # [NEW] Dunder 私有命名空间继承 (High Robustness & Zero False Positives)
    if [ -d "$dest" ]; then
        # 1. 继承入口文件 (匹配 *__custom__*，跳过 *__custom__* 目录内部)
        (cd "$dest" && find . -type d -name "*__custom__*" -prune -o \( -type f -o -type l \) -name "*__custom__*" -print0 2>/dev/null | while IFS= read -r -d '' file; do
            if [ "${NYXNIRI_TEST_MODE:-0}" = "1" ] && { [ "${file#./}" = "scratchpad-items__custom__.toml" ] || [ "${file#./}" = "orbit-items__custom__.toml" ]; }; then
                continue
            fi
            mkdir -p "$tmp_new/$(dirname "$file")"
            cp -a "$file" "$tmp_new/$file"
            msg log_keep_custom_file "${dest#"$HOME"/.config/}/${file#./}"
            if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ]; then
                # shellcheck disable=SC2088
                echo "~/.config/${dest#"$HOME"/.config/}/${file#./}" >> "$NYXNIRI_CUSTOM_LOG"
            fi
        done || true)
        # 2. 继承整套自定义目录 (连根提取 *__custom__* 目录及其内部全部文件)
        (cd "$dest" && find . -type d -name "*__custom__*" -prune -print0 2>/dev/null | while IFS= read -r -d '' dir; do
            mkdir -p "$tmp_new/$(dirname "$dir")"
            cp -a "$dir" "$tmp_new/$(dirname "$dir")/"
            msg log_keep_custom_dir "${dest#"$HOME"/.config/}/${dir#./}"
            if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ]; then
                # shellcheck disable=SC2088
                echo "~/.config/${dest#"$HOME"/.config/}/${dir#./}" >> "$NYXNIRI_CUSTOM_LOG"
            fi
        done || true)
    fi

    if [ -e "$dest" ]; then
        local old_dest="${dest}.old.$$"
        mv "$dest" "$old_dest" || return 1
        mv "$tmp_new" "$dest" || { mv "$old_dest" "$dest"; return 1; }
        ( rm -rf "$old_dest" & ) 2>/dev/null
    else
        mv "$tmp_new" "$dest"
    fi
}

atomic_replace_dir() {
    atomic_replace_item "$@"
}

_phase_atomic_deployment() {
    local items_to_deploy=("$@")
    local repo_config_dir="${REPO_DIR:-.}/$CONFIG_DIR_NAME"

    mkdir -p "$HOME/.config"

    for item in "${items_to_deploy[@]}"; do
        local src="$repo_config_dir/$item"
        local dest="$HOME/.config/$item"

        if [ -e "$src" ]; then
            local temp_monitor=""
            if [ "$item" = "$MAIN_WM" ] && [ -f "$dest/$MAIN_WM_HARDWARE_CONFIG" ]; then
                if [ "${KEEP_MONITOR:-1}" = "1" ] || [ "${NYXNIRI_KEEP_MONITOR:-0}" = "1" ]; then
                    temp_monitor=$(mktemp) || temp_monitor=""
                    if [ -n "$temp_monitor" ]; then
                        register_temp_path "$temp_monitor"
                        cp "$dest/$MAIN_WM_HARDWARE_CONFIG" "$temp_monitor"
                    fi
                fi
            fi

            atomic_replace_dir "$src" "$dest"

            if [ -n "$temp_monitor" ] && [ -f "$temp_monitor" ]; then
                cp "$temp_monitor" "$dest/$MAIN_WM_HARDWARE_CONFIG"
                rm -f "$temp_monitor" 2>/dev/null || true
                msg log_keep_monitor_config "$MAIN_WM" "$MAIN_WM_HARDWARE_CONFIG"
                if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ]; then
                    # shellcheck disable=SC2088
                    echo "~/.config/$MAIN_WM/$MAIN_WM_HARDWARE_CONFIG" >> "$NYXNIRI_CUSTOM_LOG"
                fi
            fi

            msg log_deploy_config_item "$item"
        fi
    done

    # Ensure scripts are executable and initial effects symlink exists
    for script_rel in \
        "fish/clean-cache" \
        "$THEME_ENGINE/theme-sync.sh" \
        "$THEME_ENGINE/wallpaper-hook.sh" \
        "$THEME_ENGINE/mpvpaper-sync.sh" \
        "$MAIN_WM/scripts/toggle-eyecare.sh" "$MAIN_WM/toggle-eyecare.sh" \
        "$MAIN_WM/scripts/niri-scratch-toggle.sh" "$MAIN_WM/niri-scratch-toggle.sh" \
        "$MAIN_WM/scripts/orbit-launcher.py" "$MAIN_WM/orbit-launcher.py" \
        "$MAIN_WM/scripts/niri-scratch-menu.py" "$MAIN_WM/niri-scratch-menu.py" \
        "$MAIN_WM/scripts/wallpaper-picker.py" "$MAIN_WM/wallpaper-picker.py"; do
        [ -f "$HOME/.config/$script_rel" ] && chmod +x "$HOME/.config/$script_rel"
    done
    if [ -f "$HOME/.config/$MAIN_WM/effects_normal.kdl" ] && [ ! -e "$HOME/.config/$MAIN_WM/effects.kdl" ]; then
        ln -sfn "$HOME/.config/$MAIN_WM/effects_normal.kdl" "$HOME/.config/$MAIN_WM/effects.kdl"
    fi
}

_phase_render_templates() {
    local wp_dest
    wp_dest="$(get_pics_dir)/Wallpapers"
    
    # Post-process to replace hardcoded template home paths with actual '$HOME' and '$wp_dest' for portability
    local esc_home esc_wp_dest
    esc_home=$(printf '%s\n' "$HOME" | sed 's/[|&]/\\&/g')
    esc_wp_dest=$(printf '%s\n' "$wp_dest" | sed 's/[|&]/\\&/g')

    if [ -f "$HOME/.config/$THEME_ENGINE/${THEME_ENGINE}-config.toml" ]; then
        local esc_wp_video_dest
        esc_wp_video_dest=$(printf '%s\n' "$wp_dest/video" | sed 's/[|&]/\\&/g')
        sed -i "s|^directory = \".*\"|directory = \"${esc_wp_dest}\"|" "$HOME/.config/$THEME_ENGINE/${THEME_ENGINE}-config.toml"
        sed -i "s|^video_directory = \".*\"|video_directory = \"${esc_wp_video_dest}\"|" "$HOME/.config/$THEME_ENGINE/${THEME_ENGINE}-config.toml"
        sed -i -E "s|/home/[^/]+|${esc_home}|g" "$HOME/.config/$THEME_ENGINE/${THEME_ENGINE}-config.toml"
    fi
    if [ -f "$HOME/.config/$MAIN_WM/config.kdl" ]; then
        sed -i -E "s|/home/[^/]+|${esc_home}|g" "$HOME/.config/$MAIN_WM/config.kdl"
        local pics_dir rel_pics_dir esc_rel_pics_dir
        pics_dir="$(get_pics_dir)"
        if [[ "$pics_dir" == "$HOME"* ]]; then
            rel_pics_dir="~${pics_dir#"$HOME"}"
        else
            rel_pics_dir="$pics_dir"
        fi
        esc_rel_pics_dir=$(printf '%s\n' "$rel_pics_dir" | sed 's/[|&]/\\&/g')
        sed -i -E "s|^[[:space:]]*(//)?[[:space:]]*screenshot-path .*|screenshot-path \"${esc_rel_pics_dir}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png\"|g" "$HOME/.config/$MAIN_WM/config.kdl"
    fi
    if [ -f "$HOME/.config/fish/fish_variables" ]; then
        sed -i -E "s|/home/[^/]+|${esc_home}|g" "$HOME/.config/fish/fish_variables"
    fi
}

_phase_hardware_patches() {
    # GPU Hardware Detection: Automatically uncomment NVIDIA environment variables if NVIDIA GPU is present
    if [ -f "$HOME/.config/$MAIN_WM/config.kdl" ]; then
        if command -v lspci >/dev/null 2>&1 && lspci | grep -i -q "NVIDIA"; then
            msg log_nvidia_gpu_detected
            log_msg "INFO" "NVIDIA GPU detected via lspci. Enabled NVIDIA Wayland envs in config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(GBM_BACKEND "nvidia-drm"\)|\1|g' "$HOME/.config/$MAIN_WM/config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(__GLX_VENDOR_LIBRARY_NAME "nvidia"\)|\1|g' "$HOME/.config/$MAIN_WM/config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(LIBVA_DRIVER_NAME "nvidia"\)|\1|g' "$HOME/.config/$MAIN_WM/config.kdl"
        else
            msg log_nvidia_gpu_not_detected
            log_msg "INFO" "Non-NVIDIA / Virtual Machine GPU detected. NVIDIA envs kept disabled."
        fi
    fi
}

_phase_post_install_services() {
    # Post-deployment initialization: Trigger theme-sync to apply GTK and system theme settings
    if [ -f "$HOME/.config/$THEME_ENGINE/theme-sync.sh" ]; then
        chmod +x "$HOME/.config/$THEME_ENGINE/theme-sync.sh"
        bash "$HOME/.config/$THEME_ENGINE/theme-sync.sh" >/dev/null 2>&1 || true
        msg log_gtk_theme_init
    fi

    # Enable mpvpaper plugin if CLI is available
    if command -v "$THEME_ENGINE" >/dev/null 2>&1; then
        msg log_enable_mpvpaper
        "$THEME_ENGINE" msg plugins enable noctalia/mpvpaper 2>/dev/null || true
    fi

    # Install/Update Fisher plugins if fish is available
    if command -v fish >/dev/null 2>&1; then
        msg log_check_fisher
        log_msg INFO "Checking Fisher plugin manager installation"
        local fisher_tmp
        fisher_tmp=$(mktemp) || return 0
        register_temp_path "$fisher_tmp"
        local msg_install msg_skip
        msg_install=$(msg log_install_fish_plugins)
        msg_skip=$(msg log_fisher_update_skipped)
        if fetch_raw_with_fallback "jorgebucaran/fisher" "main" "functions/fisher.fish" "$fisher_tmp"; then
            fish -c "
                if not functions -q fisher
                    source '$fisher_tmp' && fisher install jorgebucaran/fisher
                end
                if test -f ~/.config/fish/fish_plugins && functions -q fisher
                    echo \"$msg_install\"
                    fisher update || echo \"$msg_skip\"
                end
            " || true
        else
            msg log_fisher_install_skipped
            log_msg WARN "Fisher auto-install skipped (all mirrors unreachable)"
        fi
    fi
}

deploy_selected_configs() {
    local do_backup="${1:-nobackup}"
    shift || true
    local items_to_deploy=("$@")
    if [ ${#items_to_deploy[@]} -eq 0 ]; then
        items_to_deploy=("${CONFIG_ITEMS[@]}")
    fi

    if [ "$do_backup" = "backup" ]; then
        backup_configs "auto_snapshot_before_deploy" "non_interactive"
    fi

    msg copying_configs

    local _custom_log
    _custom_log=$(mktemp) || _custom_log=""
    NYXNIRI_CUSTOM_LOG="$_custom_log"
    export NYXNIRI_CUSTOM_LOG
    register_temp_path "$NYXNIRI_CUSTOM_LOG"

    _phase_atomic_deployment "${items_to_deploy[@]}"
    _phase_render_templates
    _phase_hardware_patches
    _phase_post_install_services

    msg copy_done
}

# Render the clean, minimal, zero-entropy TUI Completion Screen according to the TUI Design Charter
render_completion_screen() {
    local mode="${1:-install}"

    local title_str
    case "$mode" in
        update) title_str="$(msg summary_title_update)" ;;
        test)   title_str="$(msg summary_title_test)" ;;
        *)      title_str="$(msg summary_title_install)" ;;
    esac

    local cfg_count=0
    if [ -n "${CHOSEN_CONFIG_ITEMS+x}" ]; then
        cfg_count=${#CHOSEN_CONFIG_ITEMS[@]}
    fi

    local items_str=""
    if [ "$cfg_count" -gt 0 ]; then
        items_str=$(IFS=', '; echo "${CHOSEN_CONFIG_ITEMS[*]}")
    else
        items_str=$(IFS=', '; echo "${CONFIG_ITEMS[*]}")
    fi
    items_str="${items_str//,/, }"

    local left_missing=0
    if [ "$mode" = "full" ]; then
        check_all_deps
        for stat in "${DEP_STATUS[@]:-}"; do
            if [ "${stat:-0}" -eq 0 ]; then
                left_missing=$((left_missing + 1))
            fi
        done
    fi

    # Read and preserve custom configurations list before clearing
    local preserved_lines=()
    if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ] && [ -s "$NYXNIRI_CUSTOM_LOG" ]; then
        while IFS= read -r item; do
            [ -n "$item" ] && preserved_lines+=("$item")
        done < <(sort -u "$NYXNIRI_CUSTOM_LOG")
        rm -f "$NYXNIRI_CUSTOM_LOG" 2>/dev/null || true
        unset NYXNIRI_CUSTOM_LOG
    fi

    _render_summary_body() {
        echo -e "  \e[1;32m$title_str\e[0m\n"
        echo -e "  \e[1;37m$(msg summary_section_details)\e[0m"
        if [ "$cfg_count" -gt 0 ] || [ "$mode" = "test" ]; then
            echo -e "    \e[1;32m[✓]\e[0m $(msg summary_item_configs_ok "$items_str")"
        else
            echo -e "    \e[1;33m[!]\e[0m $(msg summary_item_configs_skip)"
        fi

        if [ "${WP_PACK_DEPLOYED:-0}" -eq 1 ] || [ "${DO_WALLPAPERS:-n}" = "y" ]; then
            echo -e "    \e[1;32m[✓]\e[0m $(msg summary_item_wallpapers_ok)"
        else
            echo -e "    \e[1;33m[!]\e[0m $(msg summary_item_wallpapers_skip)"
        fi

        if fcitx5_installed; then
            if [ "${DO_FCITX:-n}" = "y" ] || fcitx_enabled; then
                echo -e "    \e[1;32m[✓]\e[0m $(msg summary_item_fcitx_ok)"
            else
                echo -e "    \e[1;33m[!]\e[0m $(msg summary_item_fcitx_skip)"
            fi
        fi

        if [ "$mode" = "full" ]; then
            if [ "$left_missing" -eq 0 ]; then
                echo -e "    \e[1;32m[✓]\e[0m $(msg summary_item_deps_ok)"
            else
                echo -e "    \e[1;33m[!]\e[0m $(msg summary_item_deps_skip)"
            fi
        fi

        if [ "${DO_GREETER:-n}" = "y" ]; then
            echo -e "    \e[1;32m[✓]\e[0m $(msg summary_item_greeter_ok)"
        fi

        if [ ${#preserved_lines[@]} -gt 0 ]; then
            echo ""
            echo -e "  \e[1;37m$(msg summary_section_preserved)\e[0m"
            for pline in "${preserved_lines[@]}"; do
                echo -e "    $pline"
            done
        fi
    }

    # In non-interactive mode or test mode, render minimal static footer and return
    if [ ! -t 0 ] || [ ! -c /dev/tty ] || [ "$mode" = "test" ]; then
        clear 2>/dev/null || true
        show_logo
        _render_summary_body
        echo ""
        echo -e "  \e[1;37m$(msg summary_section_next)\e[0m"
        echo -e "    $(msg summary_next_start)"
        echo -e "    $(msg summary_next_manual)"
        echo -e "    $(msg summary_next_panel)"
        echo ""
        return 0
    fi

    # Interactive shortcut card with smooth in-place redraw
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        _render_summary_body

        # Section 3: 下一步 (Next Steps)
        msg summary_action_title
        _render_menu_item 0 "$(msg summary_action_apps)" "$cur_focus"
        _render_menu_item 1 "$(msg summary_action_star)" "$cur_focus"
        _render_menu_item 2 "$(msg summary_action_exit)" "$cur_focus" "subtle"

        echo ""
        msg summary_action_hint
        echo ""
        printf '\e[J'

        local key
        key=$(read_key) || break
        handle_menu_key "$key" "$cur_focus" 2
        cur_focus="$_MENU_FOCUS"

        if [ "$_MENU_ACTION" -ne -1 ]; then
            printf '\e[?25h'
            case "$_MENU_ACTION" in
                0)
                    run_optional_apps_menu_loop || true
                    clear 2>/dev/null || true
                    ;;
                1)
                    local star_url="${REPO_URL%.git}"
                    if command -v xdg-open >/dev/null 2>&1; then
                        xdg-open "$star_url" >/dev/null 2>&1 || true
                    fi
                    msg msg_star_opened "$star_url"
                    sleep 1.2
                    clear 2>/dev/null || true
                    ;;
                2)
                    return 0
                    ;;
            esac
            [ "$_MENU_ACTION" -eq 2 ] && break
        fi
    done
    printf '\e[?25h'
}

# True when the full external wallpaper pack (the video/ marker directory) is
# already deployed — used to skip redundant ~100MB re-downloads.
wallpapers_pack_present() {
    [ -d "$(get_pics_dir)/Wallpapers/video" ]
}

# Compact menu status label for the wallpaper pack (bilingual via i18n).
wallpapers_status_label() {
    if wallpapers_pack_present; then
        msg status_wallpapers_installed
    else
        msg status_wallpapers_missing
    fi
}

# Scheduling entry point used by install/update/menu flows.
# do_download="y" pulls the full external pack first; the lightweight
# fallback shipped in this repo is always synced incrementally afterwards.
deploy_wallpapers() {
    local do_download="${1:-n}"
    if [ "$do_download" = "y" ]; then
        download_wallpaper_pack
    fi
    sync_wallpapers_fallback
}

# Download the full wallpaper & video pack from the external
# ech678/wallpaper-collection repo, trying each mirror in order. The temp
# clone is stripped of its .git history and preview material so only clean
# assets land in ~/Pictures/Wallpapers. Never aborts the main flow on failure.
WP_PACK_DEPLOYED=0
download_wallpaper_pack() {
    WP_PACK_DEPLOYED=0
    msg msg_downloading_wallpapers
    if ! command -v git >/dev/null 2>&1; then
        msg msg_wallpapers_download_failed
        log_msg WARN "Wallpaper pack download skipped: git not installed"
        return 0
    fi

    local WP_MIRRORS=(
        "Official|https://github.com/ech678/wallpaper-collection.git"
        "gh-proxy.org|https://gh-proxy.org/https://github.com/ech678/wallpaper-collection.git"
    )
    local wp_dest
    wp_dest="$(get_pics_dir)/Wallpapers"
    local success=0
    local idx=1
    for item in "${WP_MIRRORS[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"
        local wp_tmp
        wp_tmp=$(mktemp -d) || { msg msg_wallpapers_download_failed; return 0; }
        register_temp_path "$wp_tmp"
        msg msg_downloading_wallpapers_node "$idx/${#WP_MIRRORS[@]}" "$tag"
        if git_clone_timeout "$url" "$wp_tmp"; then
            success=1
            break
        fi
        rm -rf "$wp_tmp" 2>/dev/null || true
        idx=$((idx + 1))
    done

    if [ "$success" -eq 1 ]; then
        mkdir -p "$wp_dest"
        rm -rf "$wp_tmp/.git" "$wp_tmp/preview.webp" "$wp_tmp/README.md" 2>/dev/null || true
        cp -an "$wp_tmp"/. "$wp_dest"/ 2>/dev/null || true
        WP_PACK_DEPLOYED=1
        msg msg_wallpapers_download_success
        log_msg INFO "Wallpaper pack deployed from [$tag] to $wp_dest"
    else
        msg msg_wallpapers_download_failed
        log_msg WARN "Wallpaper pack download failed on all mirrors"
    fi
}

# Incrementally sync the lightweight fallback wallpaper shipped in this repo
# (never overwrites existing files). Requires no network.
sync_wallpapers_fallback() {
    local wp_src="${REPO_DIR:-.}/Wallpapers"
    local wp_dest
    wp_dest="$(get_pics_dir)/Wallpapers"
    if [ ! -d "$wp_src" ]; then
        return 0
    fi
    mkdir -p "$wp_dest"
    cp -an "$wp_src"/. "$wp_dest"/ 2>/dev/null || true
    msg log_sync_wallpapers "$wp_dest"
}

run_master_component_menu() {
    local is_update="${1:-false}"
    local mode="${2:-full}"

    CHOSEN_CONFIG_ITEMS=()
    DO_FCITX="n"
    DO_GREETER="n"
    DO_WALLPAPERS="n"
    DO_BACKUP="nobackup"
    export KEEP_MONITOR=1

    declare -a MENU_ITEM_NAMES=()
    declare -a MENU_ITEM_KEYS=()
    declare -a MENU_ITEM_CHECKS=()

    for item in "${CONFIG_ITEMS[@]}"; do
        MENU_ITEM_NAMES+=("$(msg master_item_config "$item")")
        MENU_ITEM_KEYS+=("config_$item")
        MENU_ITEM_CHECKS+=(1)
    done

    local wp_check=1
    if wallpapers_pack_present; then wp_check=0; fi
    MENU_ITEM_NAMES+=("$(msg master_item_asset "Wallpapers & Videos $(wallpapers_status_label)")")
    MENU_ITEM_KEYS+=("assets_wallpapers")
    MENU_ITEM_CHECKS+=("$wp_check")

    if fcitx5_installed; then
        local fcitx_check=1
        if [ "$is_update" = true ] && ! fcitx_enabled; then
            fcitx_check=0
        fi
        MENU_ITEM_NAMES+=("$(msg master_item_module "NyxMellow fcitx5 $(fcitx_status_label)")")
        MENU_ITEM_KEYS+=("module_fcitx")
        MENU_ITEM_CHECKS+=("$fcitx_check")
    fi

    if [ "$mode" = "full" ] || [ "$is_update" = true ]; then
        local greeter_check=0
        MENU_ITEM_NAMES+=("$(msg master_item_module "Noctalia Greeter $(greeter_status_label)")")
        MENU_ITEM_KEYS+=("module_greeter")
        MENU_ITEM_CHECKS+=("$greeter_check")
    fi

    if [ "$is_update" = false ]; then
        MENU_ITEM_NAMES+=("$(msg master_item_behavior)")
        MENU_ITEM_KEYS+=("sep_behavior")
        MENU_ITEM_CHECKS+=(-1)

        MENU_ITEM_NAMES+=("$(msg master_item_backup)")
        MENU_ITEM_KEYS+=("behavior_backup")
        MENU_ITEM_CHECKS+=(1)
    fi

    local cur_focus=0
    while [ "$cur_focus" -lt "${#MENU_ITEM_NAMES[@]}" ] && [ "${MENU_ITEM_CHECKS[$cur_focus]:--1}" -eq -1 ]; do
        cur_focus=$((cur_focus + 1))
    done

    clear 2>/dev/null || true
    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg master_menu_title
        for i in "${!MENU_ITEM_NAMES[@]}"; do
            if [ "${MENU_ITEM_CHECKS[$i]:--1}" -eq -1 ]; then
                echo -e "${MENU_ITEM_NAMES[$i]}"
                continue
            fi

            local check_str="\e[90m[ ]\e[0m"
            if [ "${MENU_ITEM_CHECKS[$i]:-0}" -eq 1 ]; then
                check_str="\e[1;32m[✓]\e[0m"
            fi

            local is_focus=0
            [ "$i" -eq "$cur_focus" ] && is_focus=1
            _render_check_row "$is_focus" "$check_str" "${MENU_ITEM_NAMES[$i]}"
        done
        echo ""
        msg selective_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=$((${#MENU_ITEM_NAMES[@]} - 1))
                while [ "$cur_focus" -ge 0 ] && [ "${MENU_ITEM_CHECKS[$cur_focus]:--1}" -eq -1 ]; do
                    cur_focus=$((cur_focus - 1))
                done
                [ "$cur_focus" -lt 0 ] && cur_focus=0
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -ge "${#MENU_ITEM_NAMES[@]}" ] && cur_focus=0
                while [ "$cur_focus" -lt "${#MENU_ITEM_NAMES[@]}" ] && [ "${MENU_ITEM_CHECKS[$cur_focus]:--1}" -eq -1 ]; do
                    cur_focus=$((cur_focus + 1))
                done
                [ "$cur_focus" -ge "${#MENU_ITEM_NAMES[@]}" ] && cur_focus=$((${#MENU_ITEM_NAMES[@]} - 1))
                ;;
            SPACE)
                if [ "${MENU_ITEM_CHECKS[$cur_focus]:--1}" -ne -1 ]; then
                    if [ "${MENU_ITEM_CHECKS[$cur_focus]:-0}" -eq 1 ]; then
                        MENU_ITEM_CHECKS[cur_focus]=0
                    else
                        MENU_ITEM_CHECKS[cur_focus]=1
                    fi
                fi
                ;;
            ENTER)
                break
                ;;
            [aA])
                for i in "${!MENU_ITEM_NAMES[@]}"; do
                    [ "${MENU_ITEM_CHECKS[$i]:--1}" -ne -1 ] && MENU_ITEM_CHECKS[i]=1
                done
                ;;
            [nN])
                for i in "${!MENU_ITEM_NAMES[@]}"; do
                    [ "${MENU_ITEM_CHECKS[$i]:--1}" -ne -1 ] && MENU_ITEM_CHECKS[i]=0
                done
                ;;
            [1-9])
                local idx=$((key - 1))
                if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#MENU_ITEM_NAMES[@]}" ] && [ "${MENU_ITEM_CHECKS[$idx]:--1}" -ne -1 ]; then
                    cur_focus=$idx
                    if [ "${MENU_ITEM_CHECKS[$idx]:-0}" -eq 1 ]; then
                        MENU_ITEM_CHECKS[idx]=0
                    else
                        MENU_ITEM_CHECKS[idx]=1
                    fi
                fi
                ;;
            [qQ]|ESC)
                CHOSEN_CONFIG_ITEMS=()
                DO_FCITX="n"
                DO_GREETER="n"
                DO_WALLPAPERS="n"
                KEEP_MONITOR=0
                printf '\e[?25h'
                return 1
                ;;
        esac
    done
    printf '\e[?25h'

    for i in "${!MENU_ITEM_KEYS[@]}"; do
        local key="${MENU_ITEM_KEYS[$i]}"
        local is_checked="${MENU_ITEM_CHECKS[$i]}"
        if [ "$is_checked" -eq 1 ]; then
            if [[ "$key" == config_* ]]; then
                CHOSEN_CONFIG_ITEMS+=("${key#config_}")
            elif [ "$key" = "module_fcitx" ]; then
                DO_FCITX="y"
            elif [ "$key" = "module_greeter" ]; then
                DO_GREETER="y"
            elif [ "$key" = "assets_wallpapers" ]; then
                DO_WALLPAPERS="y"
            elif [ "$key" = "behavior_backup" ]; then
                DO_BACKUP="backup"
            fi
        fi
    done
    export KEEP_MONITOR=1
    return 0
}
offer_overwrite_upgrade() {
    local flag="${1:-}"
    if [ "$flag" = "--force" ] || [ "$flag" = "--deploy" ]; then
        deploy_selected_configs "backup"
        deploy_wallpapers "y"
        fcitx_install || true
        greeter_install || true
        render_completion_screen "update"
        return 0
    elif [ "$flag" = "--no-deploy" ]; then
        return 0
    fi

    if [ ! -t 0 ]; then
        deploy_selected_configs "nobackup"
        deploy_wallpapers
        deploy_fcitx_theme
        render_completion_screen "update"
        return 0
    fi

    local cur_focus=0

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg overwrite_title
        if [ -f "${REPO_DIR:-.}/CHANGELOG.md" ]; then
            show_release_notes "${REPO_DIR:-.}/CHANGELOG.md"
        fi

        _render_menu_item 0 "$(msg overwrite_opt1)" "$cur_focus"
        _render_menu_item 1 "$(msg overwrite_opt2)" "$cur_focus"
        _render_menu_item 2 "$(msg overwrite_opt3)" "$cur_focus" "subtle"

        echo ""
        msg submenu_hint
        echo ""
        printf '\e[J'

        local mode_choice=0
        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            mode_choice=1
        else
            local key
            key=$(read_key) || break
            handle_menu_key "$key" "$cur_focus" 2
            cur_focus="$_MENU_FOCUS"
            [ "$_MENU_ACTION" -eq -1 ] && continue
            mode_choice=$((_MENU_ACTION + 1))
        fi

        printf '\e[?25h'
        case "$mode_choice" in
            1)
                if run_master_component_menu true "full"; then
                    if [ ${#CHOSEN_CONFIG_ITEMS[@]} -gt 0 ] || [ "$DO_WALLPAPERS" = "y" ] || [ "$DO_FCITX" = "y" ] || [ "$DO_GREETER" = "y" ]; then
                        msg upgrading_selected
                        if [ ${#CHOSEN_CONFIG_ITEMS[@]} -gt 0 ]; then
                            deploy_selected_configs "$DO_BACKUP" "${CHOSEN_CONFIG_ITEMS[@]}"
                        fi
                        if [ "$DO_WALLPAPERS" = "y" ]; then
                            deploy_wallpapers "y"
                        fi
                        if [ "$DO_FCITX" = "y" ]; then
                            fcitx_install || true
                        fi
                        if [ "$DO_GREETER" = "y" ]; then
                            greeter_install || true
                        fi
                        render_completion_screen "update"
                        return 0
                    else
                        msg log_no_components_selected
                    fi
                fi
                ;;
            2)
                msg diff_viewer_title
                local repo_config_dir="${REPO_DIR:-.}/$CONFIG_DIR_NAME"
                (
                    for item in "${CONFIG_ITEMS[@]}"; do
                        local src="$repo_config_dir/$item"
                        local dest="$HOME/.config/$item"
                        if [ -e "$src" ] && [ -e "$dest" ]; then
                            diff -urN --color=always "$dest" "$src" || true
                        fi
                    done
                ) | less -R
                clear 2>/dev/null || true
                ;;
            3)
                msg log_config_deploy_skipped
                return 1
                ;;
        esac
    done
    printf '\e[?25h'
    return 1
}
_phase_preflight_check() {
    local mode="$1"
    local fcitx_available="$2"
    local do_fcitx="$3"
    local do_greeter="$4"
    local do_wallpapers="$5"

    # 1. Ask for Sudo upfront if required (Dependencies or Greeter)
    local needs_sudo=false
    if [ "$mode" = "full" ]; then
        needs_sudo=true
    fi
    if [ "$do_greeter" = "y" ]; then
        needs_sudo=true
    fi

    if [ "$needs_sudo" = true ] || [ "$mode" = "full" ]; then
        msg preflight_express_summary
        msg preflight_comp_config "${#CHOSEN_CONFIG_ITEMS[@]}"
        [ "$do_wallpapers" = "y" ] && msg preflight_comp_assets
        [ "$do_fcitx" = "y" ] && msg preflight_comp_module_fcitx "$FCITX_THEME"
        [ "$do_greeter" = "y" ] && msg preflight_comp_module_greeter "$GREETER_PKG"
        [ "$mode" = "full" ] && msg preflight_comp_deps
    fi

    if [ "$needs_sudo" = true ]; then
        msg preflight_sudo_prompt
        if sudo -v; then
            # Sudo cached successfully
            log_msg INFO "Sudo credentials cached upfront during pre-flight."
        else
            msg err_sudo_aborted
            exit 1
        fi
    fi

    # 2. Check dependencies silently (we don't install them here, we just check state)
    if [ "$mode" = "full" ]; then
        check_all_deps
    fi
}

install_configs() {
    local mode="${1:-full}"
    WP_PACK_DEPLOYED=0

    local do_backup="nobackup"
    local do_fcitx="n"
    local do_greeter="n"
    local do_wallpapers="n"
    export KEEP_MONITOR=1

    local fcitx_available=false
    if fcitx5_installed; then
        fcitx_available=true
    fi

    # ------------------------------------------------------------------
    # Phase 0: Pre-flight checklist (interactive & standardized card)
    # ------------------------------------------------------------------
    if [ -t 0 ] && [ -c /dev/tty ]; then
        if ! run_master_component_menu false "$mode"; then
            msg install_cancelled
            return 0
        fi
        do_fcitx="$DO_FCITX"
        do_greeter="$DO_GREETER"
        do_wallpapers="$DO_WALLPAPERS"
        do_backup="$DO_BACKUP"
        if [ ${#CHOSEN_CONFIG_ITEMS[@]} -eq 0 ] && [ "$do_wallpapers" = "n" ] && [ "$do_fcitx" = "n" ] && [ "$do_greeter" = "n" ]; then
            msg install_cancelled
            return 0
        fi
    else
        CHOSEN_CONFIG_ITEMS=("${CONFIG_ITEMS[@]}")
        # Non-interactive
        if ! wallpapers_pack_present; then
            do_wallpapers="y"
        fi
    fi

    _phase_preflight_check "$mode" "$fcitx_available" "$do_fcitx" "$do_greeter" "$do_wallpapers"

    # ------------------------------------------------------------------
    # Numbered steps (Uninterrupted Execution Phase)
    # ------------------------------------------------------------------
    local step_total=2
    [ "$mode" = "full" ] && step_total=$((step_total + 1))
    [ "$fcitx_available" = true ] && step_total=$((step_total + 1))
    [ "$do_greeter" = "y" ] && step_total=$((step_total + 1))
    local cur=0

    if [ "$mode" = "full" ]; then
        cur=$((cur + 1))
        msg install_step_deps "$cur/$step_total"
        for i in "${!DEPS[@]}"; do
            if [ "${DEP_STATUS[$i]:-0}" -eq 0 ]; then
                DEP_SELECT[i]=1
            else
                # shellcheck disable=SC2034
                DEP_SELECT[i]=0
            fi
        done
        install_selected_deps || true
    fi

    cur=$((cur + 1))
    msg install_step_configs "$cur/$step_total"
    if [ ${#CHOSEN_CONFIG_ITEMS[@]} -gt 0 ]; then
        deploy_selected_configs "$do_backup" "${CHOSEN_CONFIG_ITEMS[@]}"
    fi

    cur=$((cur + 1))
    msg install_step_wallpapers "$cur/$step_total"
    deploy_wallpapers "$do_wallpapers"

    if [ "$fcitx_available" = true ]; then
        cur=$((cur + 1))
        msg install_step_fcitx "$cur/$step_total"
        if [ "$do_fcitx" = "y" ] || { [ "$do_fcitx" = "n" ] && fcitx_enabled && { [ ! -t 0 ] || [ ! -c /dev/tty ]; }; }; then
            fcitx_install || true
        fi
    fi

    if [ "$do_greeter" = "y" ]; then
        cur=$((cur + 1))
        msg install_step_greeter "$cur/$step_total"
        greeter_install || true
    fi

    # ------------------------------------------------------------------
    # Completion summary
    # ------------------------------------------------------------------
    render_completion_screen "$mode"
}

# Developer test command: fast idempotent re-deploy on the real machine.
# Forces no backup, keeps monitor.kdl without asking, and skips optional
# modules / dependencies / every prompt.
test_deploy() {
    msg test_start
    export NYXNIRI_KEEP_MONITOR=1
    export NYXNIRI_TEST_MODE=1
    deploy_selected_configs "nobackup"
    deploy_wallpapers
    render_completion_screen "test"
}
