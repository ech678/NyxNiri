<div align="center">

# 🌌 NyxNiri

Personal desktop config built on Niri + Noctalia V5, for Arch / CachyOS.

<img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white" alt="OS" />
<img src="https://img.shields.io/badge/WM-Niri-89B4FA?style=for-the-badge&logo=wayland&logoColor=white" alt="WM" />
<img src="https://img.shields.io/badge/Shell-Fish%20%2B%20Starship-F9E2AF?style=for-the-badge&logo=fish&logoColor=black" alt="Shell" />
<img src="https://img.shields.io/badge/UI-Noctalia%20V5-F5C2E7?style=for-the-badge&logo=material-design&logoColor=black" alt="Bar" />

[Overview](#-overview) • [Structure](#-repository-structure) • [Features](#-key-features) • [Bindings](#️-quick-bindings) • [Install](#-installation) • [简体中文](#-项目概述)

<br/>

<img src="./preview.webp" alt="Preview" width="90%" />

</div>

## 🌌 Overview

**NyxNiri** is my personal desktop setup built around the **Niri** scroll-tiling window manager and the **Noctalia V5** shell, targeting Arch Linux and CachyOS. It pulls Material You colors from your wallpaper or live wallpaper, keeps light/dark themes in sync across the whole system, and packs in a bunch of terminal quality-of-life tweaks.

## 📂 Repository Structure

```text
NyxNiri
├── install.sh                  # Interactive bilingual installer (backups, hooks, dependencies)
├── Wallpapers/                 # Wallpaper collection (deployed to ~/Pictures/Wallpapers)
└── v2(forNoctaliaV5)/          # ✅ [Active] Current Noctalia V5 configs
    ├── niri/                   # Niri config (bindings, layout, window rules)
    ├── noctalia/               # Desktop widgets, daemon settings, automation hooks
    ├── kitty/                  # Kitty terminal config (custom shortcuts, cursor trail)
    ├── fish/                   # Fish shell (proxy helpers, aliases, cache cleaner)
    ├── fastfetch/              # Minimal system info fetch
    └── starship.toml           # Starship prompt theme
```

> [!NOTE]
> All existing configs are backed up before deployment. Wallpapers are copied to your Pictures folder.

> [!WARNING]
> The legacy DMS (Dank Material Shell) configurations have been archived and moved to the **`archive/v1-dms`** branch. The `main` branch now contains only the active V2 configs to stay clean and minimal. You can inspect the old configs by switching to that branch.

## ✨ Key Features

* **🎬 Live Wallpapers & Color Sync**:
  * `mpvpaper` for live wallpapers.
  * A Lua hook (`mpv-hook.lua`) extracts a keyframe when a video loads and passes it to Noctalia's Material You engine — terminal and desktop colors update to match.
* **🌓 Light/Dark Mode Sync (`theme-sync.sh`)**:
  * Writes to GTK 3.0/4.0 `settings.ini` and GSettings at the same time, so all GTK/Libadwaita apps switch together.
* **🐚 Fish Shell**:
  * `proxy_on` / `proxy_off` / `proxy_status` — proxy toggle + public IP check.
  * `shelly` aliases (`up`, `in`, `un`, `se`) wrapping pacman/paru for CachyOS/AUR.
  * `clean` / `clean-cache` — multi-tier cache cleaner (logs, package leftovers, runtime caches, trash).
* **💻 Kitty**:
  * GPU cursor trail (`cursor_trail`).
  * Windows-style shortcuts: `Ctrl+C` (smart copy-or-interrupt), `Ctrl+V` (paste), `Ctrl+Backspace`/`Ctrl+Delete` (word delete), `Ctrl+A` (copy full terminal buffer).

## ⌨️ Quick Bindings

| Key Combination | Action | Component |
|:---|:---|:---|
| <kbd>Super</kbd> + <kbd>Return</kbd> | Open Terminal | Kitty |
| <kbd>Super</kbd> + <kbd>Q</kbd> | Close Window | Niri |
| <kbd>Super</kbd> + <kbd>R</kbd> | App Launcher | Noctalia |
| <kbd>Super</kbd> + <kbd>E</kbd> | File Manager | Nautilus |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | Overview | Niri |
| <kbd>Super</kbd> + <kbd>H</kbd> / <kbd>L</kbd> | Column Left / Right | Niri |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | Window Down / Up | Niri |
| <kbd>Super</kbd> + <kbd>X</kbd> | Session Menu | Noctalia |
| <kbd>Super</kbd> + <kbd>I</kbd> | Settings Panel | Noctalia |
| <kbd>Super</kbd> + <kbd>V</kbd> | Clipboard History | Noctalia |

## 🚀 Installation

One-liner — the script will clone into `~/.cache/NyxNiri` on its own:

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

<details>
<summary>Manual installation</summary>

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```
</details>

## 🎨 Stack

| | |
|:---|:---|
| **WM** | Niri (scroll-tiling) |
| **Desktop Shell** | Noctalia V5 |
| **Terminal** | Kitty |
| **Shell / Prompt** | Fish + Starship |
| **Fonts** | JetBrains Mono, Noto Sans CJK SC |

<br/>

---

<div id="chinese" align="center">

[↑ English](#-nyxniri)

</div>

## 🌌 项目概述

**NyxNiri** 是我自用的桌面配置，基于 **Niri** 滚动平铺窗口管理器和 **Noctalia V5** 桌面套件，适配 Arch Linux 与 CachyOS。支持从壁纸和动态壁纸中提取 Material You 配色，全局明暗主题同步，并带有一些终端体验上的改进。

## 📂 目录结构

```text
NyxNiri
├── install.sh                  # 双语交互式安装脚本（配置备份、依赖检测、Doctor 诊断）
├── Wallpapers/                 # 壁纸库（部署至 ~/Pictures/Wallpapers）
└── v2(forNoctaliaV5)/          # ✅ [当前] Noctalia V5 配置
    ├── niri/                   # Niri 配置（快捷键、布局、窗口规则）
    ├── noctalia/               # 桌面组件、状态栏、自动配色脚本
    ├── kitty/                  # Kitty 终端配置（光标轨迹、快捷键映射）
    ├── fish/                   # Fish shell（代理函数、包管理别名、缓存清理）
    ├── fastfetch/              # 系统信息展示
    └── starship.toml           # Starship 提示符主题
```

> [!NOTE]
> 安装前会自动备份现有配置。壁纸会复制到系统图片目录。

> [!WARNING]
> 旧版的 DMS（Dank Material Shell）桌面配置已归档并移至 **`archive/v1-dms`** 分支。`main` 分支现在仅保留活跃的 V2 配置以实现极致简洁。若需参考旧配置，请在 GitHub 或本地切换到该分支查看。

## ✨ 核心特性

* **🎬 动态壁纸与自动配色**：
  * 用 `mpvpaper` 播放动态壁纸。
  * `mpv-hook.lua` 在视频加载时截一帧，交给 Noctalia 的 Material You 引擎生成配色——终端和桌面颜色跟着视频走。
* **🌓 全局明暗主题同步 (`theme-sync.sh`)**：
  * 同时写 GSettings 和 GTK 3.0/4.0 的 `settings.ini`，所有 GTK/Libadwaita 应用一起切换。
* **🐚 Fish Shell**：
  * `proxy_on` / `proxy_off` / `proxy_status` — 代理开关 + 公网 IP 检测。
  * `shelly` 别名（`up`、`in`、`un`、`se`）封装 pacman/paru。
  * `clean-cache` 多级缓存清理（日志、包残留、运行时缓存、垃圾桶）。
* **💻 Kitty 终端**：
  * GPU 光标轨迹（`cursor_trail`）。
  * Windows 风格快捷键：`Ctrl+C`（智能复制/中断）、`Ctrl+V`（粘贴）、`Ctrl+Backspace`/`Ctrl+Delete`（词级删除）、`Ctrl+A`（复制整个终端缓冲区）。

## ⌨️ 常用快捷键

| 快捷键 | 动作 | 组件 |
|:---|:---|:---|
| <kbd>Super</kbd> + <kbd>回车</kbd> | 打开终端 | Kitty |
| <kbd>Super</kbd> + <kbd>Q</kbd> | 关闭窗口 | Niri |
| <kbd>Super</kbd> + <kbd>R</kbd> | 应用启动器 | Noctalia |
| <kbd>Super</kbd> + <kbd>E</kbd> | 文件管理器 | Nautilus |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | 工作区总览 | Niri |
| <kbd>Super</kbd> + <kbd>H</kbd> / <kbd>L</kbd> | 聚焦左/右列 | Niri |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | 聚焦上/下窗口 | Niri |
| <kbd>Super</kbd> + <kbd>X</kbd> | 会话/电源菜单 | Noctalia |
| <kbd>Super</kbd> + <kbd>I</kbd> | 桌面控制中心 | Noctalia |
| <kbd>Super</kbd> + <kbd>V</kbd> | 剪贴板历史 | Noctalia |

## 🚀 部署

一行命令安装，脚本会自动克隆到 `~/.cache/NyxNiri`（内置网络检测，GitHub 不可达时自动切换国内镜像）：

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

<details>
<summary>手动安装</summary>

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```
</details>

<details>
<summary>国内镜像</summary>

```bash
# KKGitHub
curl -sL https://raw.kkgithub.com/ech678/NyxNiri/main/install.sh | bash

# GHProxy.net
curl -sL https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```
</details>

## 🎨 组件一览

* **窗口管理器**: Niri Scroll-Tiling WM
* **桌面套件 & 状态栏**: Noctalia V5 Shell
* **Shell**: Fish + Starship
* **推荐字体**: JetBrains Mono / Noto Sans CJK SC
