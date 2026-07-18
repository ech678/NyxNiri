#!/usr/bin/env bash

# ==============================================================================
# NyxNiri — Noctalia V5 & Niri Dotfiles Installer & Toolbox
# Bilingual (English/中文), menu-driven operations, config backup, doctor & update.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# ==============================================================================
# 1. Global Settings & Mode Detection
# ==============================================================================
LANG_MODE="en"
PROJECT_NAME="NyxNiri"
REPO_URL="https://github.com/ech678/NyxNiri.git"
CACHE_DIR="$HOME/.cache/NyxNiri"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect running mode
# - "repo": Running inside a local cloned repository
# - "standalone": Running as a single script file (e.g. downloaded via curl)
if [ -d "$SCRIPT_DIR/v2" ] && [ -d "$SCRIPT_DIR/Wallpapers" ]; then
    RUN_MODE="repo"
    REPO_DIR="$SCRIPT_DIR"
else
    RUN_MODE="standalone"
    REPO_DIR="$CACHE_DIR"
fi

# ==============================================================================
# 2. Translations & Internationalization (I18n)
# ==============================================================================
show_logo() {
    echo -e "\e[1;35m"
    echo " ███╗   ██╗██╗   ██╗██╗  ██╗    ███╗   ██╗██╗██████╗ ██╗"
    echo " ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ████╗  ██║██║██╔══██╗██║"
    echo " ██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██╔██╗ ██║██║██████╔╝██║"
    echo " ██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║╚██╗██║██║██╔══██╗██║"
    echo " ██║ ╚████║   ██║   ██╔╝ ██╗    ██║ ╚████║██║██║  ██║██║"
    echo " ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝"
    echo -e "\e[0m"
    echo -e "       \e[1;36mNoctalia V5 & Niri Desktop Environment Setup\e[0m"
    echo -e "       \e[1;30m--------------------------------------------\e[0m"
}

msg() {
    local key="$1"
    shift
    if [ "$LANG_MODE" = "zh" ]; then
        case "$key" in
            welcome) echo -e "\e[1;36m=== 欢迎使用 $PROJECT_NAME Dotfiles 桌面工具箱! ===\e[0m" ;;
            lang_select) echo -e "请选择语言 / Select Language:" ;;
            checking_dep) echo -e "\n\e[1;34m🔍 正在检查系统依赖项...\e[0m" ;;
            installed) echo -e "\e[1;32m[已安装]\e[0m" ;;
            missing) echo -e "\e[1;31m[未安装]\e[0m" ;;
            
            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME 控制面板主菜单 ===\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m 🚀 部署配置文件 (Deploy Configurations)" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m 📦 检查并安装依赖项 (Check & Install Dependencies)" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m 🩺 运行 System Doctor 诊断 (Run System Doctor)" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m 🛡️  仅备份当前配置 (Backup Current Configurations)" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m 🔄 更新配置与脚本 (Update Config & Script)" ;;
            menu_opt6) echo -e "  \e[1;31m6)\e[0m ❌ 退出 (Exit)" ;;
            menu_prompt) echo -e "请选择操作 [1-6]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] 无效的选项，请重新选择。\e[0m" ;;
            press_any_key) echo -e "\n按任意键返回主菜单..." ;;
            
            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m📦 请选择要安装的依赖（输入数字切换，直接回车开始安装）：\e[0m" ;;
            dep_menu_hint) echo -e "输入空格分隔的序列号（如 1 3 5）来勾选/取消，直接回车开始安装选中包：" ;;
            installing_selected) echo -e "\n\e[1;34m🚀 正在通过包管理器安装选中的依赖...\e[0m" ;;
            
            # Deployment & Backup
            backing_up) echo -e "\n\e[1;34m🛡️  安装前正在自动备份当前配置...\e[0m" ;;
            backup_done) echo -e "\e[1;32m✅ 备份完成！备份路径为: $1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m⚙️  正在部署 dotfiles 配置文件...\e[0m" ;;
            copy_done) echo -e "\e[1;32m✅ 配置文件部署与复制成功！\e[0m" ;;
            
            # System Doctor
            running_doctor) echo -e "\n\e[1;35m🩺 正在运行 System Doctor 进行系统诊断...\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[ 正常 ]\e[0m $1" ;;
            doctor_warn) echo -e "\e[1;33m[ 警告 ]\e[0m $1" ;;
            doctor_err) echo -e "\e[1;31m[ 错误 ]\e[0m $1" ;;
            all_done) echo -e "\n\e[1;32m🎉 所有的部署和诊断检查已全部完成！\e[0m" ;;
            reboot_hint) echo -e "\e[1;36m提示: 建议重启 Noctalia 或重新加载 Niri 使得所有新配置完全生效。\e[0m" ;;
            
            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] 错误: 需要安装 git 才能下载或更新配置仓库。\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m📥 检测到独立运行模式。正在克隆 NyxNiri 仓库到缓存目录 ($CACHE_DIR)... \e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m🔍 正在检查配置仓库及脚本更新...\e[0m" ;;
            updating_done) echo -e "\e[1;32m✅ 更新与重载成功！正在重新启动脚本...\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] 更新失败，请检查您的网络连接或 Git 仓库状态。\e[0m" ;;
            
            # Alerts / Prompts
            warn_deps_missing) echo -e "\n\e[1;33m⚠️  警告: 检测到你缺少一些运行所需的依赖组件！\e[0m" ;;
            ask_install_now) echo -e "是否现在检查并进入依赖安装菜单？[Y/n]: " ;;
            ask_backup_again) echo -e "检测到今天已备份过配置，是否重新备份？[y/N]: " ;;
            ask_backup_before_deploy) echo -e "是否在部署前备份当前配置？[Y/n]: " ;;
        esac
    else
        case "$key" in
            welcome) echo -e "\e[1;36m=== Welcome to $PROJECT_NAME Dotfiles Toolbox! ===\e[0m" ;;
            lang_select) echo -e "Select Language / 请选择语言:" ;;
            checking_dep) echo -e "\n\e[1;34m🔍 Checking system dependencies...\e[0m" ;;
            installed) echo -e "\e[1;32m[Installed]\e[0m" ;;
            missing) echo -e "\e[1;31m[Missing]\e[0m" ;;
            
            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME Control Panel ===\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m 🚀 Deploy Configurations" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m 📦 Check & Install Dependencies" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m 🩺 Run System Doctor Diagnostics" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m 🛡️  Backup Current Configurations Only" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m 🔄 Update Config & Script" ;;
            menu_opt6) echo -e "  \e[1;31m6)\e[0m ❌ Exit" ;;
            menu_prompt) echo -e "Please select an option [1-6]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] Invalid option, please try again.\e[0m" ;;
            press_any_key) echo -e "\nPress any key to return to main menu..." ;;
            
            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m📦 Select dependencies to install (type numbers to toggle, press Enter to confirm):\e[0m" ;;
            dep_menu_hint) echo -e "Type space-separated numbers (e.g. 1 3 5) to toggle, then press Enter to install:" ;;
            installing_selected) echo -e "\n\e[1;34m🚀 Installing selected dependencies via package manager...\e[0m" ;;
            
            # Deployment & Backup
            backing_up) echo -e "\n\e[1;34m🛡️  Automatically backing up current configs before installation...\e[0m" ;;
            backup_done) echo -e "\e[1;32m✅ Backup completed! Path: $1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m⚙️  Deploying dotfiles configuration files...\e[0m" ;;
            copy_done) echo -e "\e[1;32m✅ Configurations deployed and copied successfully!\e[0m" ;;
            
            # System Doctor
            running_doctor) echo -e "\n\e[1;35m🩺 Running System Doctor for diagnostics...\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[  OK  ]\e[0m $1" ;;
            doctor_warn) echo -e "\e[1;33m[ WARN ]\e[0m $1" ;;
            doctor_err) echo -e "\e[1;31m[ ERROR]\e[0m $1" ;;
            all_done) echo -e "\n\e[1;32m🎉 All deployment and diagnostics completed successfully!\e[0m" ;;
            reboot_hint) echo -e "\e[1;36mHint: It is recommended to restart Noctalia or reload Niri for all settings to take effect.\e[0m" ;;
            
            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] Error: git is required to download or update the repository.\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m📥 Standalone mode detected. Cloning NyxNiri repository to cache ($CACHE_DIR)... \e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m🔍 Checking for repository and script updates...\e[0m" ;;
            updating_done) echo -e "\e[1;32m✅ Update and reload successful! Restarting script...\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] Update failed. Please check your network connection or git status.\e[0m" ;;
            
            # Alerts / Prompts
            warn_deps_missing) echo -e "\n\e[1;33m⚠️  Warning: Some required dependencies are missing on your system!\e[0m" ;;
            ask_install_now) echo -e "Would you like to check and install missing dependencies now? [Y/n]: " ;;
            ask_backup_again) echo -e "A backup has already been made today. Do you want to back up again? [y/N]: " ;;
            ask_backup_before_deploy) echo -e "Do you want to back up current configs before deploying? [Y/n]: " ;;
        esac
    fi
}

select_language() {
    clear 2>/dev/null || true
    show_logo
    echo ""
    echo "  1) English"
    echo "  2) 简体中文 (Simplified Chinese)"
    echo ""
    read -p "Select Language / 请选择语言 [1/2]: " lang_choice < /dev/tty
    if [ "$lang_choice" = "2" ]; then
        LANG_MODE="zh"
    else
        LANG_MODE="en"
    fi
}

# ==============================================================================
# 3. Repository Management (Standalone Clone & Update)
# ==============================================================================
ensure_repo() {
    if [ "$RUN_MODE" = "standalone" ]; then
        if ! command -v git >/dev/null 2>&1; then
            msg git_required
            exit 1
        fi
        if [ ! -d "$CACHE_DIR" ]; then
            msg cloning_repo
            
            # Test connection to github.com
            local active_repo_url="$REPO_URL"
            echo "Testing connection to github.com..."
            if ! curl -I -s --connect-timeout 3 https://github.com >/dev/null 2>&1; then
                echo "⚠️ Connection to github.com failed. Switching to domestic mirror (KKGitHub)..."
                active_repo_url="https://kkgithub.com/ech678/NyxNiri.git"
            fi
            
            git clone "$active_repo_url" "$CACHE_DIR"
        fi
    fi
}

update_repo_and_script() {
    if ! command -v git >/dev/null 2>&1; then
        msg git_required
        return 1
    fi

    msg checking_updates
    if [ "$RUN_MODE" = "repo" ]; then
        # Inside repository
        if (cd "$REPO_DIR" && git pull); then
            msg updating_done
            sleep 1.5
            exec bash "$BASH_SOURCE" "$@"
        else
            msg updating_failed
        fi
    else
        # Standalone mode: Update cache first, then update self
        if (cd "$CACHE_DIR" && git pull); then
            if cp "$CACHE_DIR/install.sh" "$BASH_SOURCE"; then
                chmod +x "$BASH_SOURCE"
                msg updating_done
                sleep 1.5
                exec bash "$BASH_SOURCE" "$@"
            else
                echo -e "\e[1;33m⚠️  Warning: Failed to copy updated script to $BASH_SOURCE (permission issue?).\e[0m"
                echo "Please update manually from: $CACHE_DIR/install.sh"
            fi
        else
            msg updating_failed
        fi
    fi
}

# ==============================================================================
# 4. Dependency Management
# ==============================================================================
DEPS=(
    "niri"
    "noctalia"
    "fish"
    "starship"
    "kitty"
    "fastfetch"
    "eza"
    "mpvpaper"
    "ffmpeg"
    "jq"
    "inotify-tools"
    "fzf"
    "fd"
    "bat"
    "ttf-jetbrains-mono-nerd"
    "noto-fonts-cjk"
)

DEP_STATUS=()
DEP_SELECT=()

check_all_deps() {
    for i in "${!DEPS[@]}"; do
        local cmd="${DEPS[$i]}"
        local is_installed=0
        
        if [ "$cmd" = "inotify-tools" ]; then
            cmd="inotifywait"
        fi
        
        if [ "$cmd" = "ttf-jetbrains-mono-nerd" ]; then
            if fc-list : family 2>/dev/null | grep -qi "JetBrainsMono"; then
                is_installed=1
            fi
        elif [ "$cmd" = "noto-fonts-cjk" ]; then
            if fc-list : family 2>/dev/null | grep -qi "Noto Sans CJK"; then
                is_installed=1
            fi
        else
            if command -v "$cmd" >/dev/null 2>&1; then
                is_installed=1
            fi
        fi
        
        if [ "$is_installed" -eq 1 ]; then
            DEP_STATUS[$i]=1
            DEP_SELECT[$i]=0
        else
            DEP_STATUS[$i]=0
            DEP_SELECT[$i]=1
        fi
    done
}

show_dep_menu() {
    clear 2>/dev/null || true
    show_logo
    msg dep_menu_title
    for i in "${!DEPS[@]}"; do
        local status=""
        local check=" "
        
        if [ "${DEP_STATUS[$i]}" -eq 1 ]; then
            status=$(msg installed)
            check="✔"
            DEP_SELECT[$i]=0
        else
            status=$(msg missing)
            if [ "${DEP_SELECT[$i]}" -eq 1 ]; then
                check="●"
            else
                check="○"
            fi
        fi
        
        printf "  [%s] %2d) %-15s %s\n" "$check" "$((i+1))" "${DEPS[$i]}" "$status"
    done
    echo ""
    msg dep_menu_hint
}

run_dep_menu_loop() {
    while true; do
        check_all_deps
        show_dep_menu
        read -p "> " choice < /dev/tty
        if [ -z "$choice" ]; then
            break
        fi
        
        for num in $choice; do
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#DEPS[@]}" ]; then
                local index=$((num-1))
                if [ "${DEP_STATUS[$index]}" -eq 0 ]; then
                    if [ "${DEP_SELECT[$index]}" -eq 1 ]; then
                        DEP_SELECT[$index]=0
                    else
                        DEP_SELECT[$index]=1
                    fi
                fi
            fi
        done
    done
    
    install_selected_deps
}

install_selected_deps() {
    local to_install=()
    for i in "${!DEPS[@]}"; do
        if [ "${DEP_SELECT[$i]}" -eq 1 ]; then
            to_install+=("${DEPS[$i]}")
        fi
    done
    
    if [ ${#to_install[@]} -eq 0 ]; then
        return
    fi
    
    msg installing_selected
    local pkg_manager=""
    if command -v paru >/dev/null 2>&1; then
        pkg_manager="paru"
    elif command -v yay >/dev/null 2>&1; then
        pkg_manager="yay"
    else
        pkg_manager="sudo pacman"
    fi
    
    $pkg_manager -S --noconfirm "${to_install[@]}" || {
        echo "Some package installations failed. Continuing..."
    }
}

# ==============================================================================
# 5. Configuration Backup & Deployment
# ==============================================================================
backup_configs() {
    local today=$(date +%Y%m%d)
    local existing_backups=($HOME/.config/dotfiles_backup_${today}_*)
    local has_today_backup=false
    
    for d in "${existing_backups[@]}"; do
        if [ -d "$d" ]; then
            has_today_backup=true
            break
        fi
    done
    
    if [ "$has_today_backup" = true ]; then
        read -p "$(msg ask_backup_again)" choice < /dev/tty
        if [[ ! "$choice" =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi

    msg backing_up
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$HOME/.config/dotfiles_backup_$timestamp"
    mkdir -p "$backup_dir"
    
    local configs=(
        "fish"
        "noctalia"
        "niri"
        "kitty"
        "fastfetch"
        "starship.toml"
    )
    
    for item in "${configs[@]}"; do
        if [ -e "$HOME/.config/$item" ]; then
            cp -rP "$HOME/.config/$item" "$backup_dir/"
            echo "  Backed up: ~/.config/$item"
        fi
    done
    
    msg backup_done "$backup_dir"
}

install_configs() {
    # 1. Ask for backup
    read -p "$(msg ask_backup_before_deploy)" choice < /dev/tty
    if [[ "$choice" =~ ^[Yy]$ || -z "$choice" ]]; then
        backup_configs
    fi

    # 2. Deploy
    msg copying_configs
    local repo_config_dir="$REPO_DIR/v2"
    
    local configs=(
        "fish"
        "noctalia"
        "niri"
        "kitty"
        "fastfetch"
        "starship.toml"
    )
    
    mkdir -p "$HOME/.config"
    
    for item in "${configs[@]}"; do
        local src="$repo_config_dir/$item"
        local dest="$HOME/.config/$item"
        
        if [ -e "$src" ]; then
            rm -rf "$dest"
            cp -a "$src" "$dest"
            echo "  Deployed: ~/.config/$item"
        fi
    done
    
    local pics_dir=$(xdg-user-dir PICTURES 2>/dev/null || echo "$HOME/图片")
    local wp_src="$REPO_DIR/Wallpapers"
    local wp_dest="$pics_dir/Wallpapers"
    if [ -d "$wp_src" ]; then
        if [ -e "$wp_dest" ] || [ -L "$wp_dest" ]; then
            rm -rf "$wp_dest"
        fi
        mkdir -p "$pics_dir"
        cp -a "$wp_src" "$wp_dest"
        echo "  Deployed: $wp_dest"
    fi
    
    # Ensure clean-cache is executable
    if [ -f "$HOME/.config/fish/clean-cache" ]; then
        chmod +x "$HOME/.config/fish/clean-cache"
    fi

    # Post-process to replace hardcoded '/home/ray' path with the actual '$HOME' for portability
    if [ -f "$HOME/.config/noctalia/noctalia-config.toml" ]; then
        sed -i "s|/home/ray/图片/Wallpapers|$wp_dest|g" "$HOME/.config/noctalia/noctalia-config.toml"
        sed -i "s|/home/ray/图片/wallpapers|$wp_dest|g" "$HOME/.config/noctalia/noctalia-config.toml"
        sed -i "s|/home/ray|$HOME|g" "$HOME/.config/noctalia/noctalia-config.toml"
    fi
    if [ -f "$HOME/.config/niri/config.kdl" ]; then
        sed -i "s|/home/ray|$HOME|g" "$HOME/.config/niri/config.kdl"
    fi
    if [ -f "$HOME/.config/fish/fish_variables" ]; then
        sed -i "s|/home/ray|$HOME|g" "$HOME/.config/fish/fish_variables"
    fi
    
    # Install/Update Fisher plugins if fish is available
    if command -v fish >/dev/null 2>&1; then
        echo "⚙️  Installing/Updating Fisher plugins..."
        fish -c "
            if not functions -q fisher
                echo 'Fisher not found, installing fisher...'
                curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source && fisher install jorgebucaran/fisher
            end
            if test -f ~/.config/fish/fish_plugins
                echo 'Installing plugins listed in fish_plugins...'
                fisher update
            end
        "
    fi
    
    msg copy_done
    
    # 3. Prompt for dependencies if missing
    check_all_deps
    local missing_count=0
    for stat in "${DEP_STATUS[@]}"; do
        if [ "$stat" -eq 0 ]; then
            missing_count=$((missing_count + 1))
        fi
    done
    
    if [ "$missing_count" -gt 0 ]; then
        msg warn_deps_missing
        read -p "$(msg ask_install_now)" choice < /dev/tty
        if [[ "$choice" =~ ^[Yy]$ || -z "$choice" ]]; then
            run_dep_menu_loop
        fi
    fi
}

# ==============================================================================
# 6. System Diagnostics (Doctor)
# ==============================================================================
run_doctor() {
    msg running_doctor
    sleep 1
    
    if [ "$XDG_CURRENT_DESKTOP" = "niri" ]; then
        msg doctor_ok "Compositor: Niri is currently running."
    else
        msg doctor_warn "Compositor: Current desktop environment is '$XDG_CURRENT_DESKTOP' (Niri is not running)."
    fi
    
    if [ -f "/usr/share/wayland-sessions/niri.desktop" ]; then
        msg doctor_ok "Session: Niri Wayland session desktop file is registered."
    else
        msg doctor_warn "Session: /usr/share/wayland-sessions/niri.desktop is missing. (Niri might not show up on your Display Manager login screen)"
    fi
    
    if noctalia msg status >/dev/null 2>&1; then
        msg doctor_ok "Noctalia Daemon: Running and responsive."
    else
        msg doctor_err "Noctalia Daemon: Not running. (Launch: niri msg action spawn -- noctalia)"
    fi
    
    local doc_pics_dir=$(xdg-user-dir PICTURES 2>/dev/null || echo "$HOME/Pictures")
    if [ -d "$doc_pics_dir/Wallpapers" ]; then
        msg doctor_ok "Wallpapers: $doc_pics_dir/Wallpapers directory exists."
    else
        msg doctor_err "Wallpapers: $doc_pics_dir/Wallpapers directory is missing."
    fi
    
    local missing_critical=0
    for cmd in niri noctalia fish starship; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            msg doctor_err "Dependency: '$cmd' is missing from PATH."
            missing_critical=$((missing_critical + 1))
        fi
    done
    
    if [ "$missing_critical" -eq 0 ]; then
        msg doctor_ok "Core Dependencies: All core tools (niri, noctalia, fish, starship) are installed."
    fi
    
    for script in "theme-sync.sh" "wallpaper-hook.sh" "mpvpaper-sync.sh"; do
        local path="$HOME/.config/noctalia/$script"
        if [ -f "$path" ]; then
            if [ -x "$path" ]; then
                msg doctor_ok "Scripts: $script is executable."
            else
                msg doctor_warn "Scripts: $script is not executable. Fixing permissions..."
                chmod +x "$path"
            fi
        fi
    done
    
    # Check clean-cache in fish config directory
    local cc_path="$HOME/.config/fish/clean-cache"
    if [ -f "$cc_path" ]; then
        if [ -x "$cc_path" ]; then
            msg doctor_ok "Scripts: clean-cache is executable."
        else
            msg doctor_warn "Scripts: clean-cache is not executable. Fixing permissions..."
            chmod +x "$cc_path"
        fi
    else
        msg doctor_err "Scripts: clean-cache is missing from ~/.config/fish/."
    fi
    
    if [[ "$SHELL" == *fish ]]; then
        msg doctor_ok "Shell: Fish is the current default shell."
    else
        msg doctor_warn "Shell: Current shell is '$SHELL', not Fish. (Change: chsh -s \$(which fish))"
    fi
    
    msg all_done
    msg reboot_hint
}

# ==============================================================================
# 7. Command Menu & Entrypoint
# ==============================================================================
main_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg welcome
        msg menu_title
        msg menu_opt1
        msg menu_opt2
        msg menu_opt3
        msg menu_opt4
        msg menu_opt5
        msg menu_opt6
        echo ""
        read -p "$(msg menu_prompt)" opt < /dev/tty
        
        case "$opt" in
            1)
                install_configs
                read -p "$(msg press_any_key)" -n 1 < /dev/tty
                ;;
            2)
                run_dep_menu_loop
                read -p "$(msg press_any_key)" -n 1 < /dev/tty
                ;;
            3)
                run_doctor
                read -p "$(msg press_any_key)" -n 1 < /dev/tty
                ;;
            4)
                backup_configs
                read -p "$(msg press_any_key)" -n 1 < /dev/tty
                ;;
            5)
                update_repo_and_script
                read -p "$(msg press_any_key)" -n 1 < /dev/tty
                ;;
            6)
                exit 0
                ;;
            *)
                msg invalid_opt
                sleep 1.5
                ;;
        esac
    done
}

main() {
    select_language
    ensure_repo
    main_menu
}

main "$@"
