# deploy

原子部署引擎：配置文件原子替换、Dunder Protocol 保留、模板渲染、硬件补丁、壁纸部署、配置预设系统。

## 文件

- `__init__.py` — discover_config_items、atomic_replace_item、_phase_atomic_deployment、_phase_render_templates、_phase_hardware_patches、_phase_post_install_services、deploy_wallpapers、render_completion_screen、deploy_selected_configs、test_deploy、WallpaperDeployResult
- `presets.py` — 配置预设系统：list_presets、get_active_preset、set_preset、apply_preset、_load_preset_state、_save_preset_state
