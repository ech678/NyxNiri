# Changelog

## [v2.1.3] - 2026-07-23

### Added

- **install.sh**: 新增 `nyxniri snapshot [备注]` 与 `nyxniri rollback [序号]` 极简配置快照与一键回滚指令
- **install.sh**: 新增 `nyxniri uninstall` 分层安全卸载与原路复原功能，支持自动打包备份当前配置 `NyxNiri_final_backup_*.tar.gz` 并在需要时恢复最早期初始环境
- **install.sh**: 新增 `nyxniri purge` 参数，支持全套深度粉碎清理（配置、缓存、快照与壁纸）
- **install.sh**: 新增全局 `cleanup` 信号捕获句柄（`EXIT INT TERM`），防止异常或 `Ctrl+C` 中断留下残留
- **install.sh**: 在 Fish 终端 `custom_help` 中添加 `nyxniri` 快捷指令帮助说明

### Changed / Refactored

- **install.sh**: 优化快照落盘机制，统一归档至专用的 `~/.config/NyxNiri/backups/` 目录，并保持对旧版 `dotfiles_backup_*` 目录的无缝向下兼容
- **install.sh**: 移除硬编码版本号，引入 `get_version()` 自动优先解析 Git Tag（如 `v2.1.3`）与 CHANGELOG.md 标题
- **install.sh**: 运行模式中立化表述，准确标识 `Local Path` 与 `Remote Cache` 部署源
- **install.sh**: 增强软链接路径解析 `readlink -f`，解决全局调起 `nyxniri` 时的模式误判问题
- **install.sh**: 清理已失效的 `kkgithub` 镜像，更新为更稳定靠谱的国内镜像源（如 `ghproxy.net` / `bgithub.xyz`）

## [v2.1.2] - 2026-07-22

### Added

- **install.sh**: 新增一键生成 Bug Report 诊断日志功能（主菜单选项 6），导出完整的系统环境、显示器连线、软硬件版本及系统日志切片（`~/nyxniri-bug-report-*.md`）
- **install.sh**: 部署 `niri` 配置时新增 `monitor.kdl` 交互式保护，检测到已有配置时提示询问用户是否保留本地显示器布局
- **install.sh**: 新增自动注册并启用 Noctalia `mpvpaper` 插件逻辑
- **Noctalia 配置**: 默认开启 `mpvpaper` 插件、设置视频壁纸选择器浮动窗口、配置视频壁纸目录及 Bar 右侧控件
- **System Doctor**: 扩展组件诊断支持，涵盖 `swaylock` 锁屏、`wpctl` 音频、`ddcutil`/`brightnessctl` 亮度控制及 `xdg-desktop-portal` 服务状态
- **GitHub 社区与赞助**: 新增 GitHub 官方赞助配置文件 `.github/FUNDING.yml`（配置爱发电与 GitHub Sponsor）与 Issue 报告模板 `.github/ISSUE_TEMPLATE/bug_report.md`
- **README.md**: 补充社区交流群、开发者 QQ、Telegram (@Echoes678) 及其赞助支持板块，并同步了最新快捷键文档

### Changed / Refactored

- **Fastfetch**: 切换界面风格为 Catnap 圆角卡片风格 (Preset 13)
- **Niri 快捷键**: 优化动态壁纸选择器快捷键绑定为 `Mod+Shift+W` (静态壁纸维持 `Mod+W`)

### Fixed

- **install.sh**: 为 `fc-list` 增加 `command -v` 存在性保护，解决未安装 `fontconfig` 环境下 `set -e` 导致脚本意外中断退出
- **install.sh**: 增加 `xdg-user-dir PICTURES` 空值保底退守逻辑，防范图片路径拼接异常
- **install.sh**: 修正 Bug Report 导出中 `wpctl` 与 `mpvpaper` 版本信息提取，兼容非 `--version` 标志的二进制工具
- **mpvpaper-sync.sh**: 修改 `inotifywait` 为监听所在目录 `close_write,moved_to` 事件，解决应用原子写入导致 `inotify` 监听句柄丢失退出的问题
- **README.md**: 修复中英文组件一览表格表头缺失缺陷，补充 mpvpaper 引擎与壁纸快捷键说明

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
