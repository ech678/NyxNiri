# 🌌 NyxNiri — Elegantly Tiled Desktop Environment Suite

<p align="center">
  <img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-blue?style=for-the-badge&logo=arch-linux&logoColor=white" alt="OS" />
  <img src="https://img.shields.io/badge/WM-Niri-purple?style=for-the-badge&logo=wayland&logoColor=white" alt="WM" />
  <img src="https://img.shields.io/badge/Shell-Fish-orange?style=for-the-badge&logo=fish&logoColor=white" alt="Shell" />
  <img src="https://img.shields.io/badge/Status_Bar-Noctalia_V5-pink?style=for-the-badge&logo=material-design&logoColor=white" alt="Bar" />
</p>

<p align="center">
  <a href="#english">English</a> • 
  <a href="#chinese">简体中文</a>
</p>

---

<div id="english"></div>

## 🌌 Overview

Welcome to **NyxNiri**, a unified, beautifully customized tiling desktop setup based on the `Niri` scroll-tiling window manager and the `Noctalia V5` shell. Highly optimized for CachyOS / Arch Linux, this configuration provides a premium, modern user experience with dynamic Material You coloring and automated tools.

![Preview](./preview.png)

---

## 📂 Repository Structure

```text
.
├── install.sh              # Interactive, bilingual installer (Backups, Deps, Symlinks, Doctor)
├── v1(forDMS)/             # [Archived] Old Dank Material Shell (DMS) configuration
└── v2(forNoctaliaV5)/      # [Active] Latest Noctalia V5 desktop environment suite
    ├── niri/               # Latest Niri window manager config
    ├── noctalia/           # Noctalia V5 configs & robust theme-sync/hook scripts
    ├── kitty/              # Kitty terminal advanced configurations (cursor trail, etc.)
    ├── fish/               # Fish Shell config (自启动, Matugen colors, custom helpers)
    ├── fastfetch/          # Catppuccin style modular system info
    └── starship.toml       # Modern Starship prompt configuration
```

*Wallpapers are synced in a separate directory (`/home/ray/图片/Wallpapers`) and shared.*

---

## ✨ Features & Highlights

*   **🎬 Dynamic Video Wallpaper**: Seamlessly loops video wallpapers via `mpvpaper`, integrated with an automated Noctalia hook to extract terminal color schemes from video frames in real-time.
*   **🎶 Lyrics Display (Coming Soon)**: Playerctl-based synchronized desktop lyrics widgets to display real-time song lyrics.
*   **🔄 System Theme Synchronization (`theme-sync.sh`)**: Automatically updates GSettings and both GTK3/GTK4 configurations upon wallpaper or light/dark mode changes.
*   **🐚 Advanced Fish Shell & Custom Helpers**: Includes `proxy_status` (latencies & public IP geo-location), `shelly` package aliases (`up`, `in`, `un`, `se`, `clean`), and a unified `pkg_help` custom menu.
*   **⌨️ Kitty Terminal Windows-Style Keybindings**: Familiar copy/paste, backspace/delete word deletions, and smooth cursor trail fading effects.

---

## 🚀 Quick Start & Installation

NyxNiri features a fully automated, interactive, and bilingual control panel script to deploy configs safely.

```bash
# 1. Clone the Repository
git clone git@github.com:ech678/NyxNiri.git ~/项目/NyxNiri

# 2. Run the Installer
cd ~/项目/NyxNiri
./install.sh
```

---

<div id="chinese"></div>

## 🌌 项目概述

欢迎来到 **NyxNiri** 个人桌面美化与系统级深度定制仓库。本项目基于 `Niri` 滚动平铺窗口管理器与最新的 `Noctalia V5` 桌面套件，专为 CachyOS / Arch Linux 打造，集成了 Material You 壁纸色彩提取、自动化主题同步和便捷的终端管理工具，为你提供极具美感的现代化极客桌面体验。

---

## 📂 仓库目录结构

```text
.
├── install.sh              # 【核心】交互式双语部署脚本 (自动备份、依赖选装、软链部署、环境诊断)
├── v1(forDMS)/             # 【归档】旧版 Dank Material Shell (DMS) 配置
└── v2(forNoctaliaV5)/      # 【当前活动】最新 Noctalia V5 桌面环境配置套件
    ├── niri/               # 最新 Niri 窗口管理器配置
    ├── noctalia/           # Noctalia V5 配置文件及高鲁棒性的主题同步、壁纸同步钩子脚本
    ├── kitty/              # Kitty 终端的高级功能、Windows 式快捷键配色配置
    ├── fish/               # Fish Shell 配置 (自启动、壁纸色序应用、自定义增强函数与别名)
    ├── fastfetch/          # Catppuccin 风格的模块化系统看板展示
    └── starship.toml       # 极简、现代化的 Starship 提示符配置
```

*壁纸库保存在系统目录 `~/图片/Wallpapers`。*

---

## ✨ 核心特性与亮点

*   **🎬 动态视频壁纸**：由 `mpvpaper` 驱动，并与 Noctalia 的壁纸变更钩子（Hook）打通，实现动态壁纸自动生成帧缩略图并实时提取终端 Matugen 配色。
*   **🎶 歌词显示 (敬请期待)**：基于 Playerctl 的桌面歌词同步挂件，实时展示正在播放的歌曲歌词。
*   **🔄 强健的全局主题同步 (`theme-sync.sh`)**：当壁纸切换或手动改变明暗模式时，自动刷新 GSettings 和 GTK 3.0/4.0 `settings.ini`，无缝联动各类 GTK 软件。
*   **🐚 全面增强的 Fish Shell 极客终端**：
    *   提供 `proxy_status`（测速并获取中文 IP 信息和地理位置）。
    *   别名完全绑定至新版包管理器 **Shelly**（`up` 升级、`in` 安装、`un` 卸载、`se` 搜索、`clean` 清理）。
    *   输入 `pkg_help` / `my_help` 打印排版整齐的全局别名说明菜单。
*   **⌨️ Kitty 终端 Windows 式快捷键绑定**：支持 Windows 式复制/粘贴习惯、Ctrl+Backspace/Delete 快速整词删除、原生渐变指针轨迹效果。

---

## 🚀 快速上手与部署指南

NyxNiri 现已提供完全自动化的交互式控制面板脚本，支持一键式部署与无损备份。

```bash
# 1. 克隆本仓库
git clone git@github.com:ech678/NyxNiri.git ~/项目/NyxNiri

# 2. 执行安装脚本
cd ~/项目/NyxNiri
./install.sh
```

---

## 🎨 视觉效果一览
* **平铺管理器 (WM)**: Niri
* **状态栏 & 桌面组件**: Noctalia V5 Shell (含主题自动同步)
* **默认 Shell**: Fish Shell + Starship Prompt
* **主要字体**: JetBrains Mono / Noto Sans CJK SC
