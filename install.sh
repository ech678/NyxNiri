#!/usr/bin/env bash

# ==============================================================================
# NyxNiri — Noctalia & Niri Dotfiles Installer Bootstrap
# Lightweight Bash bootstrap wrapper for local execution and curl pipelines.
# Hands over execution to the native Python engine (nyxniri).
# ==============================================================================

set -euo pipefail

CACHE_DIR="$HOME/.cache/NyxNiri"
BOOTSTRAP_URL="https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh"

GIT_MIRROR_REGISTRY=(
    "Official|https://github.com/ech678/NyxNiri.git"
    "gh-proxy.org|https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"
)

git_clone_timeout() {
    local url="$1" target_dir="$2"
    local git_args=(clone)
    if [ -t 2 ]; then
        git_args+=(--progress)
    fi
    git_args+=(-c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 --depth 1 "$url" "$target_dir")
    env GIT_TERMINAL_PROMPT=0 git "${git_args[@]}"
}

clone_repo_bootstrap() {
    local target_dir="$1"
    echo -e "\e[1;34m:: Pulling repository to cache ($target_dir)…\e[0m" >&2

    local idx=1
    for item in "${GIT_MIRROR_REGISTRY[@]}"; do
        local tag="${item%%|*}"
        local url="${item#*|}"

        echo -e "  [$idx/${#GIT_MIRROR_REGISTRY[@]}] Fetching from [$tag] node…" >&2
        
        if [ "$target_dir" = "$CACHE_DIR" ] && [[ "$target_dir" == "$HOME/"* ]]; then
            rm -rf "$target_dir" 2>/dev/null || true
        fi

        if git_clone_timeout "$url" "$target_dir"; then
            echo -e "\e[1;32m[✓] Pulled from [$tag]\e[0m\n" >&2
            return 0
        fi
        idx=$((idx + 1))
    done

    echo -e "\e[1;31m[✗] All mirror nodes failed. Please check network.\e[0m" >&2
    return 1
}

exec_python_engine() {
    local target_dir="$1"
    shift

    # Only reconnect to /dev/tty if stdin is piped (e.g. curl | bash) AND no subcommand args are given
    if [ "$#" -eq 0 ] && [ ! -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; then
        PYTHONPATH="$target_dir${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m nyxniri "$@" < /dev/tty
    else
        PYTHONPATH="$target_dir${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m nyxniri "$@"
    fi
}

engine_is_complete() {
    local target_dir="$1"
    local module
    [ -f "$target_dir/install.sh" ] || return 1
    for module in __init__ __main__ backup cli constants core deploy deps doctor fcitx greeter gtktheme i18n network tui; do
        [ -f "$target_dir/nyxniri/$module.py" ] || return 1
    done
    [ -f "$target_dir/configs/niri/config.kdl" ] \
        && [ -f "$target_dir/configs/noctalia/noctalia-config.toml" ] \
        && [ -f "$target_dir/configs/fish/config.fish" ] \
        && [ -d "$target_dir/assets/wallpapers" ] \
        && [ -d "$target_dir/assets/fcitx5" ]
}

legacy_tree_detected() {
    local target_dir="$1"
    [ -f "$target_dir/lib/main.sh" ] \
        && [ -d "$target_dir/v2" ] \
        && [ ! -d "$target_dir/nyxniri" ]
}

show_legacy_migration() {
    local target_dir="$1"
    printf '\n\033[1;33m[!] Legacy Bash checkout detected: %s\033[0m\n' "$target_dir" >&2
    printf '%s\n' \
        '    The old "nyxniri update" cannot switch to the current Python layout.' \
        '    Run the current bootstrap instead:' \
        '' \
        "      curl -fsSL --connect-timeout 10 $BOOTSTRAP_URL | bash" \
        '' \
        '    Existing configs and snapshots under ~/.config are kept.' \
        '' >&2
    printf '\033[1;33m[!] 检测到旧版 Bash 仓库。旧版 "nyxniri update" 无法直接迁移到新版目录。\033[0m\n' >&2
    printf '%s\n\n' '    请运行上面的新版引导；~/.config 下的现有配置与快照不会被删除。' >&2
}

main() {
    # 1. Prevent running as root
    if [ "$(id -u)" -eq 0 ]; then
        echo -e "\n\e[1;31m[✗] Do not run as root. Re-run as normal user: ./install.sh\e[0m\n" >&2
        exit 1
    fi

    # 2. Determine script location and stop legacy checkouts before bootstrapping.
    local real_script="" script_dir=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        real_script="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
        script_dir="$(cd "$(dirname "$real_script")" 2>/dev/null && pwd)"
    fi
    if [ -n "$script_dir" ] && legacy_tree_detected "$script_dir"; then
        show_legacy_migration "$script_dir"
        exit 2
    fi

    # 3. Check for python3
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "\e[1;31m[✗] python3 is required but missing. Please install Python 3.10+ first.\e[0m" >&2
        exit 1
    fi
    local python_version py_major py_minor
    python_version="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')" || {
        echo -e "\e[1;31m[✗] Could not determine the Python version. Please install Python 3.10+.\e[0m" >&2
        exit 1
    }
    IFS=. read -r py_major py_minor <<< "$python_version"
    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
        echo -e "\e[1;31m[✗] Python 3.10+ is required (found $python_version). Please upgrade python3 and retry.\e[0m" >&2
        exit 1
    fi

    # 4. Local repository execution
    if [ -n "$script_dir" ] \
        && { [ -d "$script_dir/nyxniri" ] || [ -d "$script_dir/configs" ] || [ -d "$script_dir/assets" ]; }; then
        if ! engine_is_complete "$script_dir"; then
            echo -e "\e[1;31m[✗] NyxNiri source is incomplete: $script_dir\e[0m" >&2
            echo "    Restore or clone the repository again, then rerun ./install.sh." >&2
            exit 1
        fi
        exec_python_engine "$script_dir" "$@"
    fi

    # 5. Standalone / Cache execution
    if ! command -v git >/dev/null 2>&1; then
        echo -e "\e[1;31m[✗] git is missing. Please install git first.\e[0m" >&2
        exit 1
    fi

    if [ -d "$CACHE_DIR/.git" ] && ! engine_is_complete "$CACHE_DIR"; then
        echo -e "\e[1;33m[!] Cached source is incomplete; rebuilding it…\e[0m" >&2
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    elif [ ! -d "$CACHE_DIR/.git" ]; then
        clone_repo_bootstrap "$CACHE_DIR" || exit 1
    else
        echo -e "\e[1;34m:: Updating cache repository…\e[0m" >&2
        if [ -t 2 ]; then
            git -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 -c http.connectTimeout=10 -c http.timeout=20 -C "$CACHE_DIR" pull --ff-only --progress || cache_update_failed=1
        else
            git -c http.lowSpeedTime=15 -c http.lowSpeedLimit=1000 -c http.connectTimeout=10 -c http.timeout=20 -C "$CACHE_DIR" pull --ff-only --quiet >/dev/null 2>&1 || cache_update_failed=1
        fi
        if [ "${cache_update_failed:-0}" -eq 1 ]; then
            echo -e "\e[1;33m[!] Cache update failed; continuing with the last complete copy.\e[0m" >&2
        fi
    fi

    if engine_is_complete "$CACHE_DIR"; then
        exec_python_engine "$CACHE_DIR" "$@"
    else
        echo -e "\e[1;31m[✗] Cached source is still incomplete: $CACHE_DIR\e[0m" >&2
        echo "    Check the network, then run the bootstrap again." >&2
        exit 1
    fi
}

main "$@"
