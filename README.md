# 🌌 NyxNiri — Ultimate Scroll-Tiling Desktop Setup

<p align="center">
  <img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white" alt="OS" />
  <img src="https://img.shields.io/badge/WM-Niri%20Scroll--Tiling-89B4FA?style=for-the-badge&logo=wayland&logoColor=white" alt="WM" />
  <img src="https://img.shields.io/badge/Shell-Fish%20%2B%20Starship-F9E2AF?style=for-the-badge&logo=fish&logoColor=white" alt="Shell" />
  <img src="https://img.shields.io/badge/Bar%20%26%20UI-Noctalia%20V5%20Shell-F5C2E7?style=for-the-badge&logo=material-design&logoColor=white" alt="Bar" />
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-repository-structure">Repository Structure</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#-quick-bindings">Quick Bindings</a> •
  <a href="#-installation">Installation</a> •
  <a href="#chinese">简体中文</a>
</p>

---

## 🌌 Overview

**NyxNiri** is a premium, scroll-tiling desktop setup powered by the **Niri** window manager and the **Noctalia V5** shell framework. Designed for Arch Linux and CachyOS, it features seamless Material You color extraction from wallpapers, responsive layout dynamics, global theme synchronizations, and an optimized terminal environment.

![Preview](./preview.webp)

---

## 📂 Repository Structure

```text
NyxNiri
├── install.sh                  # Interactive bilingual installer (backups, hooks, dependencies)
├── Wallpapers/                 # Curated wallpaper collections (deployed to ~/Pictures/Wallpapers)
├── v1(forDMS)/                 # [Archived] Old DMS (Dank Material Shell) configurations
└── v2(forNoctaliaV5)/          # [Active] Latest Noctalia V5 configurations
    ├── niri/                   # Niri configuration (bindings, layout, window rules)
    ├── noctalia/               # Desktop widgets, daemon settings, and automation hooks
    ├── kitty/                  # GPU-accelerated terminal config (custom shortcuts, trails)
    ├── fish/                   # Fish shell integrations (proxy helpers, aliases, clean script)
    ├── fastfetch/              # Minimal sys-info fetch screen
    └── starship.toml           # Multi-layered prompt theme
```

> [!NOTE]
> All configs are safely backed up before deployment. Wallpapers are dynamically linked to your default Pictures folder.

---

## ✨ Key Features

* **🎬 Dynamic Video Wallpapers & Color Sync**: 
  * Seamless integration with `mpvpaper` for high-performance video wallpapers.
  * An automated Lua hook (`mpv-hook.lua`) extracts keyframes from videos on the fly, allowing Noctalia's Material You engine to generate matching terminal and desktop color palettes.
* **🌓 Unified Light/Dark Mode (`theme-sync.sh`)**:
  * Automatically synchronizes GTK 3.0/4.0 settings, GSettings, and application theme modes (prefer-light/prefer-dark) globally upon theme switching.
* **🐚 Optimized Terminal Experience (Fish Shell)**:
  * Built-in proxy utilities: `proxy_on` (enable proxy), `proxy_off` (disable proxy), and `proxy_status` (diagnose proxy connectivity and retrieve public geo-IP).
  * Unified CachyOS/AUR package management wrappers via `shelly` (`up`, `in`, `un`, `se`).
  * A robust, multi-tier system cache cleaner (`clean` -> `clean-cache`).
* **💻 Power-user Terminal (Kitty)**:
  * Enables smooth GPU cursor trail rendering (`cursor_trail`).
  * Native Windows-style shortcuts mapping: `Ctrl+C` (intelligent copy or interrupt), `Ctrl+V` (paste), `Ctrl+Backspace`/`Ctrl+Delete` (word-by-word deletion), and `Ctrl+A` (copy entire terminal history to clipboard).

---

## ⌨️ Quick Bindings

| Key Combination | Action | Component |
|:---|:---|:---|
| <kbd>Super</kbd> + <kbd>Return</kbd> | Open Terminal | Kitty |
| <kbd>Super</kbd> + <kbd>Q</kbd> | Close Window | Niri |
| <kbd>Super</kbd> + <kbd>R</kbd> | Toggle App Launcher | Noctalia |
| <kbd>Super</kbd> + <kbd>X</kbd> | Toggle Session Menu | Noctalia |
| <kbd>Super</kbd> + <kbd>V</kbd> | Toggle Clipboard History | Noctalia |
| <kbd>Super</kbd> + <kbd>I</kbd> | Toggle Settings Panel | Noctalia |
| <kbd>Super</kbd> + <kbd>E</kbd> | Open File Manager | Nautilus |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | Toggle Overview Mode | Niri |
| <kbd>Super</kbd> + <kbd>H</kbd> / <kbd>L</kbd> | Column Left / Right | Niri |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | Window Down / Up | Niri |

---

## 🚀 Installation

Ensure your system is up-to-date, then clone and run the bilingual menu-driven setup:

```bash
# Clone the repository
git clone git@github.com:ech678/NyxNiri.git ~/NyxNiri

# Execute the installer
cd ~/NyxNiri
./install.sh
```

---

<div id="chinese"></div>

## 🌌 项目概述

**NyxNiri** 是一个基于 **Niri** 滚动平铺窗口管理器与 **Noctalia V5** 桌面套件的极致美化与效率配置方案。原生适配 Arch Linux 与 CachyOS，深度集成了 Material You 视频/壁纸色彩动态提取、全局跨应用主题同步以及高度定制的现代终端环境。

<p align="center">
  <a href="#-overview">English Documentation</a>
</p>

---

## 📂 目录结构

```text
NyxNiri
├── install.sh                  # 双语交互式安装脚本（包含配置备份、依赖检测、Doctor 诊断）
├── Wallpapers/                 # 精选壁纸库（自动部署至系统图片目录下的 Wallpapers/ 目录）
├── v1(forDMS)/                 # [已归档] 旧版 DMS 桌面套件配置
└── v2(forNoctaliaV5)/          # [当前激活] Noctalia V5 桌面环境配置
    ├── niri/                   # Niri 窗口管理器配置（快捷键、窗口模糊、游戏性能规则）
    ├── noctalia/               # 桌面组件、状态栏面板与自动配色同步脚本
    ├── kitty/                  # GPU 加速终端配置（包含渐变光标轨道与 Windows 快捷键映射）
    ├── fish/                   # Fish shell 设置（自启动、代理快捷函数与统一包管理别名）
    ├── fastfetch/              # 极简系统看板信息展示
    └── starship.toml           # 终端 Starship 多色状态提示符
```

> [!NOTE]
> 安装前脚本会安全地自动备份你现有的配置。壁纸文件会自动根据系统语言环境适配部署到对应的图片文件夹中。

---

## ✨ 核心特性

* **🎬 动态视频壁纸与色彩同步**：
  * 无缝集成 `mpvpaper`，支持流畅的动态视频壁纸渲染。
  * 内置 `mpv-hook.lua` 钩子，在加载视频时自动截取关键帧，动态生成 Material You 色彩主题，使终端与桌面配色与视频画面自动契合。
* **🌓 全局明暗主题同步 (`theme-sync.sh`)**：
  * 在切换壁纸或明暗模式时，自动且同步地刷新 GSettings 及 GTK 3.0/4.0 的 `settings.ini` 配置文件，保证所有 GTK/Libadwaita 应用外观一致。
* **🐚 极致顺滑的 Fish Shell 环境**：
  * **便捷代理管理**：提供 `proxy_on`、`proxy_off` 控制命令，以及 `proxy_status` 测速与 IP 地理位置检测工具。
  * **现代包管理别名**：继承了 CachyOS 推荐的 `shelly` 统一包管理别名（`up` 升级、`in` 安装、`un` 卸载）。
  * **一键缓存清理**：集成 `clean-cache` 脚本，可按需清理系统日志、包管理残留、各语言运行时缓存与用户垃圾桶。
* **💻 现代 Kitty 终端优化**：
  * 配置了流畅的 GPU 渐变光标轨迹（`cursor_trail`）。
  * 支持符合直觉的快捷键映射：`Ctrl+C`（智能复制/中断）、`Ctrl+V`（粘贴）、`Ctrl+Backspace`/`Ctrl+Delete`（词级向前/向后删除），以及 `Ctrl+A`（一键复制整个终端历史缓冲区到剪贴板）。

---

## ⌨️ 常用快捷键

| 快捷键 | 执行动作 | 所属组件 |
|:---|:---|:---|
| <kbd>Super</kbd> + <kbd>回车</kbd> | 打开终端 | Kitty 终端 |
| <kbd>Super</kbd> + <kbd>Q</kbd> | 关闭当前窗口 | Niri 窗口管理器 |
| <kbd>Super</kbd> + <kbd>R</kbd> | 开启/关闭 应用启动器 | Noctalia 面板 |
| <kbd>Super</kbd> + <kbd>X</kbd> | 开启/关闭 会话电源菜单 | Noctalia 面板 |
| <kbd>Super</kbd> + <kbd>V</kbd> | 开启/关闭 剪贴板历史 | Noctalia 面板 |
| <kbd>Super</kbd> + <kbd>I</kbd> | 开启/关闭 桌面控制中心 | Noctalia 面板 |
| <kbd>Super</kbd> + <kbd>E</kbd> | 打开文件管理器 | Nautilus |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | 切换多工作区总览 (Overview) | Niri 窗口管理器 |
| <kbd>Super</kbd> + <kbd>H</kbd> / <kbd>L</kbd> | 聚焦左侧 / 右侧列 | Niri 窗口管理器 |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | 聚焦下方 / 上方窗口 | Niri 窗口管理器 |

---

## 🚀 部署指南

提供交互式安装脚本，会安全地自动备份你现有的配置：

```bash
# 克隆仓库
git clone git@github.com:ech678/NyxNiri.git ~/NyxNiri

# 运行安装器
cd ~/NyxNiri
./install.sh
```

---

## 🎨 视觉与细节

* **窗口管理器**: Niri Scroll-Tiling WM
* **桌面套件 & 状态栏**: Noctalia V5 Shell (基于 Quickshell)
* **默认 Shell**: Fish Shell + Starship Prompt
* **推荐字体**: JetBrains Mono (等宽) / Noto Sans CJK SC (中文字体)
