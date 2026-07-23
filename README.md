<div align="right">

[简体中文](#项目概述)

</div>

<div align="center">

<a id="nyxniri"></a>

# 𝑁𝑦𝑥𝑁𝑖𝑟𝑖

_A calm, Material You desktop — Niri + Noctalia V5, for Arch / CachyOS_

<img src="https://img.shields.io/badge/License-GPLv3-89B4FA?style=flat-square" alt="license" />
<img src="https://img.shields.io/github/stars/ech678/NyxNiri?style=flat-square&color=F5C2E7&label=stars" alt="stars" />
<img src="https://img.shields.io/badge/CLI-nyxniri-A6E3A1?style=flat-square&logo=gnu-bash&logoColor=black" alt="CLI" />
<img src="https://img.shields.io/badge/OS-Arch%20%7C%20CachyOS-1793D1?style=flat-square&logo=arch-linux&logoColor=white" alt="OS" />
<img src="https://img.shields.io/badge/WM-Niri-89B4FA?style=flat-square&logo=wayland&logoColor=white" alt="WM" />
<img src="https://img.shields.io/badge/Shell-Fish%20%2B%20Starship-F9E2AF?style=flat-square&logo=fish&logoColor=black" alt="Shell" />
<img src="https://img.shields.io/badge/UI-Noctalia%20V5-F5C2E7?style=flat-square&logo=material-design&logoColor=black" alt="Bar" />

<br/>
<br/>

<img src="./preview.webp" alt="Preview" width="90%" />

📺 [Video preview on Bilibili](https://www.bilibili.com/video/BV1Q1KV66EWX)

</div>

<br/>

## Overview

**NyxNiri** is my personal desktop setup, built around the **Niri**
scroll-tiling window manager and the **Noctalia V5** shell, for Arch Linux and
CachyOS. It pulls Material You color palettes from a static or live wallpaper,
keeps light/dark theming in sync across the whole system, and layers in a
handful of terminal quality-of-life improvements.

<br/>

## 🛠️ NyxNiri Management CLI (`nyxniri`)

NyxNiri comes with a built-in lightweight management tool `nyxniri` for snapshots, rollbacks, and diagnostics:

| Command | Action / Purpose | Notes |
| :--- | :--- | :--- |
| `nyxniri` | Open interactive TUI control panel | Fast menu-driven access |
| `nyxniri snapshot [note]` | Create a manual configuration snapshot | Saved to `~/.config/NyxNiri/backups/` |
| `nyxniri rollback [index]` | Rollback configuration to a historical snapshot | Auto-saves pre-rollback safety snapshot |
| `nyxniri list` | List all available configuration snapshots | Displays timestamp & note |
| `nyxniri uninstall` | Safely uninstall NyxNiri (with auto archive) | Supports `--safe` or `--restore` |
| `nyxniri purge` | Deep purge all NyxNiri configs, cache & wallpapers | Complete cleanup |
| `nyxniri doctor` | Run System Doctor diagnostics | Health check for desktop components |

<br/>

## Installation

### ⚡ Quick One-liner Install (Curl Pipe)

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

### 📦 Recommended Method (Git Repository)

Clone the repository to your local machine for full git history and offline control:

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

<details>
<summary>🌐 Domestic Mirror (For users in China)</summary>

```bash
# Via GHProxy Mirror
curl -sL https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

</details>

<br/>

## Stack

| Component          | Choice / Details                 |
| :----------------- | :------------------------------- |
| **WM**             | Niri (scroll-tiling)             |
| **Desktop shell**  | Noctalia V5                      |
| **Live wallpaper** | mpvpaper                         |
| **Terminal**       | Kitty                            |
| **Shell / prompt** | Fish + Starship                  |
| **Fonts**          | JetBrains Mono, Noto Sans CJK SC |

<br/>

## Acknowledgments

<!-- Add more entries the same way: - [user/repo](url) — one-line reason -->

- [RanXom/glassy-niri](https://github.com/RanXom/glassy-niri) — reference for
  blur settings

<br/>

## Recommended Projects

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) —
  desktop lyrics widget for Noctalia
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity)
  — automatically adjusts browser opacity for watching videos under Niri

<br/>

## FAQ & Troubleshooting

### Noctalia is slow to start after logging into Niri

If the wallpaper, bar, and widgets take several seconds — or minutes — to appear
after login, check these two common causes first:

**1. DDC/CI monitor scanning blocks startup (I2C timeout)** — Noctalia probes
the I2C bus via `ddcutil` to detect monitor brightness controls. On some
hardware — especially with NVIDIA drivers — this scan hangs the whole startup
sequence.

_Fix:_ disable DDC/CI under `[brightness]` in
`~/.config/noctalia/noctalia-config.toml`:

```toml
[brightness]
enable_ddcutil = false
```

**2. Corrupted local plugin repositories** — If the git index of a cached plugin
repo gets corrupted or desynced, the `git checkout` Noctalia runs to unpack
plugins on startup will hang. Check `~/.cache/noctalia/noctalia.log` for lines
like `git checkout ... took 20000ms`.

_Fix:_ force-reset the plugin caches:

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

<br/>

## 💬 Community & Contact

If you encounter issues, find a bug, or want to discuss Linux ricing:

- 🐧 **Developer QQ**: `2040244628`
- ✈️ **Telegram**: [@Echoes678](https://t.me/Echoes678)
- 💬 **Linux Ricing QQ Group**: `631425889`
- 🐛 **Submit a Bug Report**: Run `./install.sh` and select `6) 🐛 Generate Bug Report` to export diagnostic logs, or open an [Issue](https://github.com/ech678/NyxNiri/issues) on GitHub.

<br/>

## 💖 Support & Sponsor

Maintaining NyxNiri requires continuous testing, script optimization, and documentation updates. If this project improved your Linux experience:

- ☕️ **Sponsor via Afdian**: [afdian.com/a/Echoes678](https://afdian.com/a/Echoes678)
- ⭐️ **GitHub Star**: If you like this project, please consider leaving a Star on GitHub! Your support is my greatest motivation!

<br/>

---

<div align="right">

[↑ English](#nyxniri)

</div>

## 项目概述

**NyxNiri** 是我自用的桌面配置，基于 **Niri** 滚动平铺窗口管理器和 **Noctalia
V5** 桌面套件，适配 Arch Linux 与 CachyOS。支持从静态或动态壁纸中提取 Material
You 配色，全局明暗主题同步，并带有一些终端体验上的改进。

<br/>

## 目录结构

```text
NyxNiri
├── install.sh                  # 双语交互式安装脚本（配置备份、依赖检测、Doctor 诊断）
├── Wallpapers/                 # 壁纸库（部署至 ~/Pictures/Wallpapers）
└── v2/                         # ✅ [当前] Noctalia V5 配置
    ├── niri/                   # Niri 配置 — 快捷键、布局、窗口规则
    ├── noctalia/                # 桌面组件、状态栏、自动配色脚本
    ├── kitty/                  # Kitty 终端配置 — 光标轨迹、快捷键映射
    ├── fish/                   # Fish shell — 代理函数、包管理别名、缓存清理
    ├── fastfetch/               # 系统信息展示
    └── starship.toml           # Starship 提示符主题
```

> [!NOTE]
> 安装前会自动备份现有配置，壁纸会复制到系统图片目录 —— 不会静默覆盖任何文件。

> [!WARNING]
> 旧版的 DMS（Dank Material Shell）配置已归档至
> **[`archive/v1-dms`](../../tree/archive/v1-dms)** 分支。`main`
> 分支现在只保留活跃的 V2 配置，刻意维持简洁。

<br/>

## 核心特性

**动态壁纸与自动配色** — `mpvpaper` 播放动态壁纸；`mpv-hook.lua`
在视频加载时截取关键帧，交给 Noctalia 的 Material You
引擎实时生成配色，终端与桌面颜色随壁纸联动。

**全局明暗主题同步** — `theme-sync.sh` 同时写入 GSettings 与 GTK 3.0/4.0 的
`settings.ini`，所有 GTK/Libadwaita 应用一起切换。

**Fish Shell**

- `proxy_on` / `proxy_off` / `proxy_status` — 代理开关 + 公网 IP 检测
- `shelly` 别名（`up`、`in`、`un`、`se`）封装 pacman/paru，覆盖 CachyOS + AUR
- `clean` / `clean-cache` — 分级缓存清理（日志、包残留、运行时缓存、垃圾桶）

**Kitty 终端**

- GPU 加速光标轨迹（`cursor_trail`）
- Windows 风格快捷键：`Ctrl+C` 智能复制/中断、`Ctrl+V` 粘贴、`Ctrl+Backspace` /
  `Ctrl+Delete` 词级删除、`Ctrl+A` 复制整个终端缓冲区

<br/>

## 常用快捷键

**窗口与布局**

| 快捷键                                         | 动作              |
| :--------------------------------------------- | :---------------- |
| <kbd>Super</kbd> + <kbd>回车</kbd>             | 打开终端（Kitty） |
| <kbd>Super</kbd> + <kbd>Q</kbd>                | 关闭窗口          |
| <kbd>Super</kbd> + <kbd>T</kbd>                | 切换窗口浮动      |
| <kbd>Super</kbd> + <kbd>F</kbd>                | 最大化当前列      |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | 全屏当前窗口      |
| <kbd>Super</kbd> + <kbd>Tab</kbd>              | 工作区总览        |
| <kbd>Super</kbd> + <kbd>H</kbd> / <kbd>Z</kbd> | 聚焦左列          |
| <kbd>Super</kbd> + <kbd>C</kbd>                | 聚焦右列          |
| <kbd>Super</kbd> + <kbd>J</kbd> / <kbd>K</kbd> | 聚焦上 / 下窗口   |

**系统与桌面套件（Noctalia）**

| 快捷键                          | 动作                   |
| :------------------------------ | :--------------------- |
| <kbd>Super</kbd> + <kbd>R</kbd> | 应用启动器             |
| <kbd>Super</kbd> + <kbd>E</kbd> | 文件管理器（Nautilus） |
| <kbd>Super</kbd> + <kbd>X</kbd> | 会话/电源菜单          |
| <kbd>Super</kbd> + <kbd>I</kbd> | 桌面控制中心           |
| <kbd>Super</kbd> + <kbd>V</kbd> | 剪贴板历史             |
| <kbd>Super</kbd> + <kbd>W</kbd> | 静态壁纸选择器         |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>W</kbd> | 动态视频壁纸选择器     |
| <kbd>Super</kbd> + <kbd>L</kbd> | 锁屏                   |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | 区域截图               |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | 重载 Niri 配置文件     |

<br/>

## 🛠️ NyxNiri 管理命令行工具 (`nyxniri`)

NyxNiri 内置了极简管理工具 `nyxniri`，方便随时手动打快照、回滚配置与诊断：

| 指令 | 作用描述 | 备注 |
| :--- | :--- | :--- |
| `nyxniri` | 打开交互式桌面控制面板主菜单 | 快捷控制台菜单 |
| `nyxniri snapshot [备注]` | 手动创建当前配置快照 | 保存至 `~/.config/NyxNiri/backups/` |
| `nyxniri rollback [序号]` | 恢复指定的历史配置快照 | 恢复前自动生成预保护快照 |
| `nyxniri list` | 列出所有可用的配置快照 | 查看时间与快照备注 |
| `nyxniri uninstall` | 安全卸载并复原系统配置环境 | 支持归档备份与原路复原 |
| `nyxniri purge` | 彻底深度清理所有配置、缓存与壁纸 | 强迫症专属粉碎 |
| `nyxniri doctor` | 运行 System Doctor 系统诊断 | 诊断桌面与系统依赖健康状态 |

<br/>

## 部署

### ⚡ 一行命令极速安装 (Curl 管道)

```bash
curl -sL https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

### 📦 推荐安装方式（Git 仓库部署）

将项目克隆到本地后运行安装脚本，方便随时修改配置与离线管理：

```bash
git clone https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

<details>
<summary>🌐 国内网络加速</summary>

```bash
# 通过 GHProxy 镜像节点
curl -sL https://ghproxy.net/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

</details>

<br/>

## 组件一览

| 组件类型           | 选用软件 / 详细配置               |
| :----------------- | :------------------------------- |
| **窗口管理器**     | Niri（滚动平铺）                 |
| **桌面套件**       | Noctalia V5                      |
| **动态壁纸引擎**   | mpvpaper                         |
| **终端**           | Kitty                            |
| **Shell / 提示符** | Fish + Starship                  |
| **字体**           | JetBrains Mono, Noto Sans CJK SC |

<br/>

## 致谢

<!-- 以后加新条目照这个格式加一行就行: - [user/repo](url) — 一句话说明 -->

- [RanXom/glassy-niri](https://github.com/RanXom/glassy-niri) — 借鉴了 blur
  相关设置

<br/>

## 推荐项目

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) —
  Noctalia 歌词显示插件
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity)
  — 自动调节浏览器透明度（为了方便看视频）

<br/>

## 常见问题与故障排除

### 登录 Niri 后，Noctalia 要等很久才启动

如果状态栏和桌面组件登录后卡住很久才出现，先排查以下两个最常见的原因：

**1. DDC/CI 显示器亮度扫描阻塞（I2C 超时）** — Noctalia 默认通过 `ddcutil` 扫描
I2C 总线以检测外接显示器亮度控制。在部分硬件、尤其是 NVIDIA
独显环境下，这一扫描会严重超时并阻塞整个启动流程。

_解决办法：_ 在 `~/.config/noctalia/noctalia-config.toml` 的 `[brightness]`
下禁用 DDC/CI：

```toml
[brightness]
enable_ddcutil = false
```

**2. 本地插件 Git 仓库缓存状态损坏** — 若本地缓存的插件仓库元数据损坏，Noctalia
启动时解包插件所执行的 `git checkout` 会陷入阻塞。可检查
`~/.cache/noctalia/noctalia.log` 中是否有 `git checkout ... took xxxxxms`
之类的记录。

_解决办法：_ 对本地插件仓库执行硬重置：

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

<br/>

## 💬 社区交流与反馈

如果你在配置使用过程中遇到问题、发现 BUG，或者想交流 Linux 桌面美化（Ricing）经验：

- 🐧 **开发者 QQ**：`2040244628`
- ✈️ **Telegram**：[@Echoes678](https://t.me/Echoes678)
- 💬 **Linux Ricing 交流群**：`631425889`
- 🐛 **提交 Bug Report**：运行 `./install.sh` 菜单中的 `6) 🐛 生成 Bug Report 报告` 导出诊断日志，或直接在 GitHub 提交 [Issue](https://github.com/ech678/NyxNiri/issues)。

<br/>

## 💖 赞助与支持

维护 NyxNiri 项目需要持续的硬件测试、脚本优化与文档更新。如果这个项目提升了你的 Linux 使用体验：

- ☕️ **爱发电赞助**：[afdian.com/a/Echoes678](https://afdian.com/a/Echoes678)
- ⭐️ **GitHub Star**：如果喜欢本项目，欢迎在 GitHub 上点个 Star！你的支持是持续创作的最大动力！


