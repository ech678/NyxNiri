# Changelog

## [v2.1.1] - 2026-07-21

### Added

- **install.sh**: 更新成功后自动渲染 `CHANGELOG.md` 最新版本更新日志并暂停等待按键确认

### Fixed

- **Fish 配置**: `eza --icons` → `--icons=auto`，兼容新版 eza 参数校验
- **Fish 配置**: `set -gx PATH` → `fish_add_path -m`，避免重复追加 PATH
- **install.sh**: 依赖分为官方源/AUR 两类，纯 pacman 环境自动跳过 AUR 包并提示 (解决 Issue #1)
- **install.sh**: 使用 `LC_ALL=C` 解析 `pacman` 输出，消除系统 Locale 差异导致的检查失效
- **install.sh**: 规范化 `mpvpaper` 版本提取（剥离 Epoch/修订号），修复 Bash 算术比较抛错 (解决 Issue #2)
- **install.sh**: 优化 `mpvpaper-git` 检查与平滑升级流程，防止预先卸载造成软件包丢失
- **clean-cache**: 移除主脚本作用域内的 `local` 关键字，消除运行时 Bash 报错
- **mpvpaper-sync.sh**: 缩略图生成改用 PID 临时文件 + `mv` 原子替换，防止并发竞争写入损坏
- **Niri 配置**: 移除 auto-Niri.fish，修复 greetd 会话启动时的死循环
