# NyxNiri Module Architecture (Decoupled)

## Module Dependency Graph

```
colors.py          ANSI color constants (zero dependency)
urls.py            Repository URLs and mirror registries (zero dependency)
deps_list.py       Package dependency lists (zero dependency)
utils.py           Shared helpers: _text(), _remove_path(), _copy_path()
version.py         Changelog/git version extraction
env.py             Environment context, path resolution, get_pics_dir()
lock.py            fcntl single-instance lock
log.py             Rolling log engine
cleanup.py         Temp path registry + atexit cleanup
symlink.py         CLI binary symlink management
i18n.py            Bilingual message dictionary + get_lang/set_lang/msg
tui.py             Terminal UI: Menu, CheckboxList, key reader, logo, rendering
constants.py       Project identity (re-exports colors/urls/deps_list)
core.py            Facade re-exporting env/lock/log/cleanup/symlink/version
network.py         Git clone, raw fetch, safe_git_pull (multi-mirror)
deploy_core.py     Atomic deployment, template render, hardware patches, post-install
deploy.py          Facade re-exporting deploy_core + wallpapers + completion
wallpapers.py      Wallpaper pack download + offline fallback sync
completion.py      TUI completion screen rendering
backup.py          Snapshot, rollback, delete, uninstall management
deps.py            System dependency detection, AUR bootstrap, optional apps install
doctor.py          System health diagnostics + bug report exporter
fcitx.py           NyxMellow fcitx5 dynamic skin module
greeter.py         Noctalia Greeter (greetd login) module
gtktheme.py        GTK Material You theme module
cli.py             CLI dispatcher + interactive menu loops
__main__.py        Entry point: python3 -m nyxniri
```

## Decoupling Principles Applied

1. **Single Responsibility**: Each module owns exactly one concern.
2. **No God Modules**: cli.py (674 lines) split into menus + commands; deploy.py (571 lines) split into deploy_core + wallpapers + completion.
3. **No Duplicate Code**: _text(), _remove_path(), _copy_path() consolidated into utils.py.
4. **Constants Split**: colors.py (ANSI), urls.py (mirrors), deps_list.py (packages), constants.py (identity only).
5. **Core Split**: env.py (paths), version.py, lock.py, log.py, cleanup.py, symlink.py; core.py is now a thin facade.
6. **Backward Compatibility**: core.py and deploy.py remain as facades so existing `from nyxniri.core import ...` imports continue to work.
