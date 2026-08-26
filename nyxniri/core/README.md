# core

核心运行时基础设施：路径解析、环境检测、文件锁、日志、版本号、临时路径管理、symlink 保障。

## 文件

- `__init__.py` — Environment 类、get_env、acquire_lock、init_logger、log_msg、ensure_nyxniri_symlink、cleanup_temp_paths、get_pics_dir、get_version、release_lock
- `constants.py` — 全局常量：CLI_CMD、MAIN_WM、THEME_ENGINE、REPO_URL、GIT_MIRROR_REGISTRY、CORE_DEPS、AUR_DEPS、OPTIONAL_APPS、Colors
