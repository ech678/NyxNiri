# configs

Dotfiles 配置源码，通过 atomic_replace_item 原子部署到 ~/.config/。

## 配置单元

- fish — Fish Shell 配置（config.fish、completions、clean-cache 多文件拆分）
- kitty — Kitty 终端（kitty.conf + presets: transparent/opaque）
- niri — Niri WM（config.kdl + 多模块 include + scripts/ + presets: compact/spacious）
- fastfetch — 系统信息（config.jsonc + presets: full/compact）
- zed — Zed 编辑器（settings.json + keymap.json + presets: vscode/jetbrains）
- noctalia — Noctalia 引擎（theme-sync.sh、wallpaper-hook.sh、templates/、noctalia-config.toml）
- starship.toml — Starship 提示符配置（被 Noctalia 动态注入配色）
- xdg-desktop-portal — 门户配置

## Dunder Protocol

文件名含 __custom__ 的文件/目录在更新时自动保留，不被覆盖。
