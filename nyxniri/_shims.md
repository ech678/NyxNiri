# shims

兼容层文件，从对应包重新导出全部公共符号，保持 `from nyxniri.xxx import yyy` 路径不变。

## 文件

- `cli.py` — 从 nyxniri.cli 包重新导出 main、COMMANDS、install_configs_workflow、main_menu_loop、print_help、exit_usage 等
- `core.py` — 从 nyxniri.core 包重新导出 Environment、get_env、acquire_lock、init_logger、log_msg、ensure_nyxniri_symlink 等
- `deploy.py` — 从 nyxniri.deploy 包重新导出 atomic_replace_item、list_presets、set_preset、deploy_selected_configs 等
- `i18n.py` — 从 nyxniri.i18n 包重新导出 msg、get_lang、set_lang、TRANSLATIONS
- `tui.py` — 从 nyxniri.ui 包重新导出 Menu、MenuItem、CheckboxList、prompt_confirm、show_logo 等
- `constants.py` — 从 nyxniri.core.constants 重新导出全部常量（CLI_CMD、Colors、REPO_URL、CORE_DEPS 等）
