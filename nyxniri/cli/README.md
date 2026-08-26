# cli

命令行入口与交互式控制面板。

## 文件

- `__init__.py` — main() 入口、COMMANDS 字典注册、命令分发
- `commands.py` — 各子命令 handler：_cmd_install、_cmd_snapshot、_cmd_rollback、_cmd_preset、_cmd_theme、_cmd_update 等
- `menus.py` — 交互式菜单与工作流：install_configs_workflow、offer_overwrite_upgrade、main_menu_loop、snapshot_menu_loop、deps_menu_loop、print_help、exit_usage
