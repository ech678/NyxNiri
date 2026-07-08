# 🌌 Niri & Noctalia Desktop Dotfiles

<p align="center">
  <a href="#-niri--noctalia-desktop-dotfiles">English</a> • 
  <a href="#-niri--noctalia-desktop-dotfiles-zh">简体中文</a>
</p>

![Preview](./preview.png)

Welcome to my personal Linux desktop configuration and customization repository. This repository has been refactored and is now divided into two main version branches, containing my latest configurations for the `Niri` scroll-tiling window manager and the `Noctalia V5` desktop suite.

---

## 📂 Repository Structure

To save storage space and standardize version management, this repository is designed with a parallel structure:

```text
.
├── v1(forDMS)/             # [Archived] Old Dank Material Shell (DMS) configuration
│   ├── kitty/              # Old Kitty terminal color scheme and keybindings
│   ├── niri/               # Old Niri config (including dms modular configuration)
│   └── DankMaterialShell/  # Old DMS shell suite configuration and plugins
├── v2(forNoctaliaV5)/      # [Active] Latest Noctalia V5 desktop environment configuration suite
│   ├── niri/               # Latest Niri window manager config (cleaned of history redundancy and backups)
│   ├── noctalia/           # Noctalia V5 configuration files and core theme sync scripts
│   ├── kitty/              # Kitty terminal advanced features and keybindings
│   ├── fish/               # Fish Shell config (auto-start Niri, Material You terminal color sequence application)
│   ├── fastfetch/          # Catppuccin style modular system information display
│   └── starship.toml       # Minimalist, modern Starship prompt configuration
└── wallpapers/             # [Shared Wallpaper Library] Synced with system wallpaper directory, shared by both generations to save storage
```

---

## ✨ v2(forNoctaliaV5) New Features & Upgrades

The new `v2` configuration introduces modern desktop aesthetics and deep system-level optimizations:

### 1. 🔄 System Theme Synchronization (`theme-sync.sh`)
* **Mechanism**: Based on the `theme_mode_changed` hook provided by `Noctalia`. When the wallpaper changes or the theme mode is toggled (light/dark), the script `/v2(forNoctaliaV5)/noctalia/theme-sync.sh` is automatically executed.
* **Sync Scope**:
  * Automatically updates **GSettings** (updates `color-scheme` and `gtk-theme` under `org.gnome.desktop.interface`).
  * Dynamically updates **GTK 3.0** (`settings.ini`) and **GTK 4.0** (`settings.ini`) configuration files to seamlessly transition Firefox, Chromium, VS Code, and other GTK/Adwaita applications.

### 2. 🐚 Advanced Fish Shell Integration
* **tty1 Auto-Start**: Includes `auto-Niri.fish` logic to automatically launch a Niri session when logging into tty1.
* **Material You Terminal Colors**: Reads and applies terminal sequence colors (`sequences.txt`) extracted from the wallpaper, keeping terminal colors in sync with your wallpaper changes.
* **Proxy Helpers**: Simple `proxy_on` and `proxy_off` functions to quickly toggle terminal proxy settings.
* **Handy Aliases**: Integrates `eza` with icons and fixes an issue in Kitty where running `clear` didn't fully clear the scrollback history.

### 3. 📛 Modular Capsule Bar Design
* Features a new **Capsule status bar** design with a translucent background, rounded corners, and edge glows.
* Integrates a complete suite of components: Application Launcher, workspace switcher, active window titles, media controls, system tray drawer, wallpaper control, volume/notification, and session management.

### 4. ⌨️ Kitty Terminal Windows-Style Keybindings
* Supports Windows-style copy/paste behavior (`Ctrl+C` for smart copy/interrupt, `Ctrl+V` to paste).
* Supports `Ctrl+Backspace` to delete a word backward, and `Ctrl+Delete` to delete a word forward.
* Supports `Ctrl+A` to copy the entire terminal scrollback history to the clipboard.
* Enables Kitty's native `cursor_trail` fading pointer effect.

---

## 🚀 Quick Start & Installation Guide

Follow these steps to back up your original configurations and link the folders to deploy this setup.

> [!CAUTION]
> Make sure to back up your existing configurations before creating symbolic links (`ln -s`) to prevent data loss.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/niri-kitty-dotfiles.git ~/项目/dotfiles
```

### 2. Deploy v2(forNoctaliaV5) Configurations

```bash
# Back up existing configs
mv ~/.config/niri ~/.config/niri.bak
mv ~/.config/noctalia ~/.config/noctalia.bak
mv ~/.config/kitty ~/.config/kitty.bak
mv ~/.config/fish ~/.config/fish.bak
mv ~/.config/fastfetch ~/.config/fastfetch.bak
mv ~/.config/starship.toml ~/.config/starship.toml.bak

# Create symbolic links
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/niri ~/.config/niri
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/noctalia ~/.config/noctalia
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/kitty ~/.config/kitty
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/fish ~/.config/fish
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/fastfetch ~/.config/fastfetch
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/starship.toml ~/.config/starship.toml
```

### 3. Link Wallpapers
```bash
# If your wallpaper directory doesn't exist, link it to your Pictures directory
ln -s ~/项目/dotfiles/wallpapers ~/图片/wallpapers
```

---

## 🎨 Visual Highlights
* **Window Manager (WM)**: Niri
* **Status Bar & UI**: Noctalia V5 Shell (includes `theme-sync` utility)
* **Default Shell**: Fish + Starship Prompt
* **Main Fonts**: JetBrains Mono / Noto Sans CJK SC

---
---

# 🌌 Niri & Noctalia Desktop Dotfiles (ZH)

欢迎来到我的个人 Linux 桌面美化配置文件仓库。本仓库经过重构，现已划分为两个主要版本分支，并包含了我最新的 `Niri` 滚动平铺窗口管理器与 `Noctalia V5` 桌面套件的配置。

---

## 📂 仓库目录结构

本仓库为了节约存储空间并规范版本管理，采用如下的并列结构设计：

```text
.
├── v1(forDMS)/             # 【归档】旧版 Dank Material Shell (DMS) 配置
│   ├── kitty/              # 旧版 Kitty 终端配色及快捷键
│   ├── niri/               # 旧版 Niri 配置（包含 dms 模块化配置）
│   └── DankMaterialShell/  # 旧版 DMS 壳套件配置与插件
├── v2(forNoctaliaV5)/      # 【当前活动】最新 Noctalia V5 桌面环境配置套件
│   ├── niri/               # 最新 Niri 窗口管理器配置（已清理历史冗余与备份）
│   ├── noctalia/           # Noctalia V5 配置文件及核心主题同步脚本
│   ├── kitty/              # Kitty 终端的高级功能与快捷键配置
│   ├── fish/               # Fish Shell 配置（自启动 Niri、Material You 终端色序应用）
│   ├── fastfetch/          # Catppuccin 风格的模块化系统看板展示
│   └── starship.toml       # 极简、现代化的 Starship 提示符配置
└── wallpapers/             # 【共享壁纸库】与系统壁纸目录保持同步，两代配置共享以节省存储
```

---

## ✨ v2(forNoctaliaV5) 全新升级特性

在全新的 `v2` 配置中，引入了诸多现代化的桌面美化方案和系统级深度优化功能：

### 1. 🔄 系统主题同步功能 (`theme-sync.sh`)
* **原理**：基于 `Noctalia` 提供的 `theme_mode_changed` 钩子，当壁纸或手动切换主题模式（明/暗）时，自动触发 `/v2(forNoctaliaV5)/noctalia/theme-sync.sh` 脚本。
* **同步范围**：
  * 自动修改 **GSettings** 接口（`org.gnome.desktop.interface` 的 `color-scheme` 与 `gtk-theme`）。
  * 动态更新 **GTK 3.0** (`settings.ini`) 和 **GTK 4.0** (`settings.ini`) 配置文件，无缝改变 Firefox、Chromium、VS Code 等主流 GTK/Adwaita 软件的视觉模式。

### 2. 🐚 全新的 Fish Shell 支持与深度整合
* **tty1 自动启动桌面**：加入 `auto-Niri.fish` 逻辑，在登录 tty1 时无感直接拉起 Niri 滚动窗口会话。
* **Material You 终端色序应用**：能够直接读取并应用壁纸提取生成的终端序列色（`sequences.txt`），实现终端配色随壁纸变换而实时统一。
* **便捷终端代理**：提供 `proxy_on` 与 `proxy_off` 快捷函数，一键开关终端网络代理。
* **实用别名**：整合了 `eza` 图标别名，并修复了 Kitty 终端在执行 `clear` 时滚屏历史不彻底清除的问题。

### 3. 📛 模块化胶囊 Bar 美化设计
* 采用全新的**胶囊型（Capsule）状态栏**设计，半透明背景，支持圆角和边缘发光。
* 整合了包括应用启动器 (Launcher)、多工作区控制、活动窗口标题展示、媒体控制、系统托盘抽屉 (Tray Drawer)、系统壁纸控制与音量/通知/会话管理等全套功能组件。

### 4. ⌨️ Kitty 终端 Windows 式易用性绑定
* 支持 Windows 式复制/粘贴习惯（`Ctrl+C` 智能复制/中断，`Ctrl+V` 粘贴）。
* 支持 `Ctrl+Backspace` 快速删除整词，`Ctrl+Delete` 向后删除整词。
* 支持 `Ctrl+A` 一键复制终端所有滚屏历史到剪贴板。
* 启用原生 `cursor_trail` 渐变指针轨迹效果。

---

## 🚀 快速上手与安装参考

如果你想在自己的系统上部署并使用这一套配置，请按照以下步骤备份并链接相应文件夹。

> [!CAUTION]
> 在执行符号链接（`ln -s`）前，请务必提前备份你的原有配置，以免数据丢失。

### 1. 克隆本仓库
```bash
git clone https://github.com/your-username/niri-kitty-dotfiles.git ~/项目/dotfiles
```

### 2. 部署 v2(forNoctaliaV5) 桌面配置

```bash
# 备份你的原有配置
mv ~/.config/niri ~/.config/niri.bak
mv ~/.config/noctalia ~/.config/noctalia.bak
mv ~/.config/kitty ~/.config/kitty.bak
mv ~/.config/fish ~/.config/fish.bak
mv ~/.config/fastfetch ~/.config/fastfetch.bak
mv ~/.config/starship.toml ~/.config/starship.toml.bak

# 创建软链接
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/niri ~/.config/niri
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/noctalia ~/.config/noctalia
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/kitty ~/.config/kitty
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/fish ~/.config/fish
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/fastfetch ~/.config/fastfetch
ln -s ~/项目/dotfiles/v2\(forNoctaliaV5\)/starship.toml ~/.config/starship.toml
```

### 3. 软链接壁纸库
```bash
# 如果你的壁纸目录不存在，可以将其链接到你的图片库中
ln -s ~/项目/dotfiles/wallpapers ~/图片/wallpapers
```

---

## 🎨 视觉效果一览
* **平铺管理器 (WM)**: Niri
* **状态栏 & 桌面组件**: Noctalia V5 Shell (含 `theme-sync` 主题同步)
* **默认 Shell**: Fish + Starship Prompt
* **主要字体**: JetBrains Mono / Noto Sans CJK SC
