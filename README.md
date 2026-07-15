# 🌌 NyxNiri — Elegantly Tiled Desktop Environment Suite

<p align="center">
  <a href="#-nyxniri--elegantly-tiled-desktop-environment-suite">English</a> • 
  <a href="#-nyxniri--elegantly-tiled-desktop-environment-suite-zh">简体中文</a>
</p>

![Preview](./preview.png)

Welcome to **NyxNiri**, a unified, beautifully customized tiling desktop setup based on the `Niri` scroll-tiling window manager and the `Noctalia V5` shell. Highly optimized for CachyOS / Arch Linux, this configuration provides a premium, modern user experience with dynamic Material You coloring and automated tools.

---

## 📂 Repository Structure

```text
.
├── install.sh              # [New] Interactive, bilingual installer (Backups, Deps, Symlinks, Doctor)
├── v1(forDMS)/             # [Archived] Old Dank Material Shell (DMS) configuration
│   ├── kitty/              # Old Kitty terminal configuration
│   ├── niri/               # Old Niri config
│   └── DankMaterialShell/  # Old DMS shell suite configuration and plugins
├── v2(forNoctaliaV5)/      # [Active] Latest Noctalia V5 desktop environment suite
│   ├── niri/               # Latest Niri window manager config
│   ├── noctalia/           # Noctalia V5 configs & robust, portable hook scripts
│   ├── kitty/              # Kitty terminal advanced features & Windows-style shortcuts
│   ├── fish/               # Fish Shell config (自启动, Matugen colors, custom helpers)
│   ├── fastfetch/          # Catppuccin style modular system info
│   └── starship.toml       # Modern Starship prompt configuration
└── Wallpapers/             # [Shared Wallpapers] Synced with ~/图片/Wallpapers (with video/ loop wallpapers)
```

---

## ✨ v2(forNoctaliaV5) Highlights & Features

### 1. 🔄 Seamless Theme Synchronization (`theme-sync.sh`)
* Powered by Noctalia's `theme_mode_changed` hook. Toggling light/dark mode or changing wallpapers automatically triggers theme synchronization.
* **Scope**: Updates **GSettings** (Gnome interface color-scheme/gtk-theme) and both **GTK 3.0** & **GTK 4.0** `settings.ini` to keep Firefox, VS Code, and other GTK/Adwaita applications perfectly aligned.

### 2. 🐚 Advanced Fish Shell & Custom Helpers
* **tty1 Auto-Start**: Automatically launches a Niri session upon logging into tty1.
* **Material You Colors**: Applies active color sequences (`sequences.txt`) extracted from the wallpaper.
* **Proxy Tools**: `proxy_on` and `proxy_off` toggle environment variables; `proxy_status` queries international connectivity and prints your public IP & location in Chinese.
* **Shelly Integration**: Package management aliases mapped to CachyOS's default package manager **Shelly**:
  * `up` / `update` -> `shelly upgrade-all` (Updates Pacman repos, AUR, Flatpak, and AppImages in one go).
  * `in` -> `shelly install`
  * `un` -> `shelly remove`
  * `se` -> `shelly query`
  * `clean` -> `shelly purify && shelly cache-clean`
  * `pkg_help` / `my_help` -> Prints a custom, formatted help menu detailing all custom aliases and proxy functions.

### 3. 📛 Modular Capsule Bar Design
* Translucent Capsule status bar with rounded corners and glowing borders.
* Complete tray widget drawer, media controls, wallpaper settings, and session actions.

### 4. ⌨️ Kitty Terminal Enhancements
* Supports Windows-style keyboard habits (`Ctrl+C` smart copy, `Ctrl+V` paste, `Ctrl+Backspace`/`Ctrl+Delete` word deletions).
* Native `cursor_trail` fading trajectory pointer enabled.

---

## 🚀 Quick Start & Installation

NyxNiri now features a fully automated, interactive, and bilingual control panel script to deploy configs safely.

### 1. Clone the Repository
```bash
git clone git@github.com:ech678/NyxNiri.git ~/项目/NyxNiri
```

### 2. Run the Installer
```bash
cd ~/项目/NyxNiri
./install.sh
```

### 3. Let the Script Do the Work
* **Language**: Select English or Chinese.
* **Dependencies**: Scan for missing tools and install them interactively (supporting `yay` or `pacman`).
* **Backup**: Auto-backup any existing configurations in `~/.config` into a timestamped directory (e.g. `~/.config/dotfiles_backup_YYYYMMDD_HHMMSS/`).
* **Deploy**: Safely link all configurations to `~/.config/` and link the Wallpapers folder to `~/图片/Wallpapers`.
* **System Doctor**: Scan the compositor, daemon responsiveness, script executable permissions, and environment health automatically.

---

## 🎨 Visual Specifications
* **Window Manager**: Niri
* **Desktop Shell & Widgets**: Noctalia V5 Shell
* **Interactivity**: Fish Shell + Starship Prompt
* **Core Fonts**: JetBrains Mono / Noto Sans CJK SC

---
---

# 🌌 NyxNiri — 优雅的平铺桌面环境配置套件 (ZH)

欢迎来到 **NyxNiri** 个人桌面美化与系统级深度定制仓库。本项目基于 `Niri` 滚动平铺窗口管理器与最新的 `Noctalia V5` 桌面套件，专为 CachyOS / Arch Linux 打造，集成了 Material You 壁纸色彩提取、自动化主题同步和便捷的终端管理工具，为你提供极具美感的现代化极客桌面体验。

---

## 📂 仓库目录结构

```text
.
├── install.sh              # 【全新】交互式双语部署脚本 (自动备份、依赖选装、软链部署、环境诊断)
├── v1(forDMS)/             # 【归档】旧版 Dank Material Shell (DMS) 配置
│   ├── kitty/              # 旧版 Kitty 终端配置
│   ├── niri/               # 旧版 Niri 配置
│   └── DankMaterialShell/  # 旧版 DMS 壳套件配置与插件
├── v2(forNoctaliaV5)/      # 【当前活动】最新 Noctalia V5 桌面环境配置套件
│   ├── niri/               # 最新 Niri 窗口管理器配置
│   ├── noctalia/           # Noctalia V5 配置文件及高鲁棒性的主题同步、壁纸同步钩子脚本
│   ├── kitty/              # Kitty 终端的高级功能、Windows 式快捷键配色配置
│   ├── fish/               # Fish Shell 配置 (自启动、壁纸色序应用、自定义增强函数与别名)
│   ├── fastfetch/          # Catppuccin 风格的模块化系统看板展示
│   └── starship.toml       # 极简、现代化的 Starship 提示符配置
└── Wallpapers/             # 【共享壁纸库】与系统 ~/图片/Wallpapers 保持同步，包含 video/ 动态壁纸
```

---

## ✨ v2(forNoctaliaV5) 核心升级特性

### 1. 🔄 强健的全局主题同步 (`theme-sync.sh`)
* 基于 Noctalia 的 `theme_mode_changed` 钩子，当壁纸切换或手动改变明暗模式时，自动执行同步脚本。
* **同步范围**：自动同步 **GSettings** 接口（color-scheme 与 gtk-theme）以及 **GTK 3.0** & **GTK 4.0** 的 `settings.ini` 配置文件，实现 Firefox、Chromium、VS Code 等第三方软件的主题无感自动切换。

### 2. 🐚 全面增强的 Fish Shell 极客终端
* **tty1 自动启动**：登录 tty1 控制台时，自动且无缝地直接拉起 Niri 滚动窗口会话。
* **Material You 终端色序**：直接读取并应用壁纸提取生成的终端序列色 (`sequences.txt`)，保持终端配色与壁纸实时统一。
* **代理与状态查询**：提供 `proxy_on` 与 `proxy_off` 快捷函数，以及新增的 `proxy_status`（测速并获取中文 IP 信息和地理位置）。
* **Shelly 包管理器深度整合 (CachyOS 推荐)**：别名完全绑定至新版包管理器 **Shelly**，快捷键如下：
  * `up` / `update` ➡️ `shelly upgrade-all` (一键升级 Pacman 官方包、AUR、Flatpak 以及 AppImage，极度省心)。
  * `in` ➡️ `shelly install` (安装)
  * `un` ➡️ `shelly remove` (卸载)
  * `se` ➡️ `shelly query` (搜索)
  * `clean` ➡️ `shelly purify && shelly cache-clean` (清理冗余包与本地缓存)
  * `pkg_help` / `my_help` ➡️ 打印排版整齐的全局自定义别名/代理命令的使用帮助菜单。

### 3. 📛 模块化胶囊 Bar 美化设计
* 采用全新半透明圆角边缘发光**胶囊型（Capsule）状态栏**，支持多工作区、活动窗口标题、媒体控制、系统托盘抽屉 (Tray Drawer)、系统壁纸控制与音量/通知管理。

### 4. ⌨️ Kitty 终端 Windows 式快捷键绑定
* 支持 Windows 式复制/粘贴习惯（`Ctrl+C` 智能复制/中断，`Ctrl+V` 粘贴）。
* 支持 `Ctrl+Backspace` / `Ctrl+Delete` 快速整词删除。
* 启用原生 `cursor_trail` 渐变指针轨迹效果。

---

## 🚀 快速上手与部署指南

NyxNiri 现已提供完全自动化的交互式控制面板脚本，支持一键式部署与无损备份。

### 1. 克隆本仓库
```bash
git clone git@github.com:ech678/NyxNiri.git ~/项目/NyxNiri
```

### 2. 执行安装脚本
```bash
cd ~/项目/NyxNiri
./install.sh
```

### 3. 部署步骤流程
* **选择语言**：支持英文与中文交互。
* **依赖检测**：扫描系统缺少包，并提示你选择安装（支持 `yay` 或 `pacman`）。
* **自动备份**：安装前自动将你 `~/.config` 下的冲突目录备份至带有时戳的目录（如 `~/.config/dotfiles_backup_YYYYMMDD_HHMMSS/`）。
* **自动软链**：将仓库配置软链接至 `~/.config/`，并将壁纸库软链接至 `~/图片/Wallpapers`。
* **环境医生**：System Doctor 会自动诊断窗口管理器运行状态、后台守护进程活性、配套脚本可执行权限等。

---

## 🎨 视觉效果一览
* **平铺管理器 (WM)**: Niri
* **状态栏 & 桌面组件**: Noctalia V5 Shell (含主题自动同步)
* **默认 Shell**: Fish + Starship Prompt
* **主要字体**: JetBrains Mono / Noto Sans CJK SC
