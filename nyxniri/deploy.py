"""Deployment facade: re-exports from deploy_core, wallpapers, and completion."""
from nyxniri.deploy_core import (
    discover_config_items,
    atomic_replace_item,
    deploy_selected_configs,
    test_deploy,
    _phase_atomic_deployment,
    _phase_render_templates,
    _phase_hardware_patches,
    _phase_post_install_services,
)
from nyxniri.wallpapers import (
    deploy_wallpapers,
    wallpapers_pack_present,
    WallpaperDeployResult,
)
from nyxniri.completion import render_completion_screen
