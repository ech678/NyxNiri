# nyxniri 命令补全 (NyxNiri Dotfiles Management Tool)
# Auto-loaded by fish from ~/.config/fish/completions/nyxniri.fish

# 子命令
complete -c nyxniri -f -n "__fish_use_subcommand" -a install   -d "Deploy dotfiles & deps (full|config)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a snapshot  -d "Create or delete config snapshots"
complete -c nyxniri -f -n "__fish_use_subcommand" -a rollback  -d "Restore config from a snapshot"
complete -c nyxniri -f -n "__fish_use_subcommand" -a list      -d "List all snapshots"
complete -c nyxniri -f -n "__fish_use_subcommand" -a uninstall -d "Safely uninstall NyxNiri"
complete -c nyxniri -f -n "__fish_use_subcommand" -a purge     -d "Deep purge configs, snapshots, cache & wallpapers"
complete -c nyxniri -f -n "__fish_use_subcommand" -a doctor    -d "Run System Doctor diagnostics"
complete -c nyxniri -f -n "__fish_use_subcommand" -a deps      -d "Open dependency check & install menu"
complete -c nyxniri -f -n "__fish_use_subcommand" -a apps      -d "Recommended apps installer (Nautilus/Fcitx5)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a wallpapers -d "Download full wallpaper & video pack"
complete -c nyxniri -f -n "__fish_use_subcommand" -a theme     -d "Switch/sync system dark/light theme (toggle|dark|light|sync|status)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a bug       -d "Generate a diagnostic bug report"
complete -c nyxniri -f -n "__fish_use_subcommand" -a report    -d "Generate a diagnostic bug report"
complete -c nyxniri -f -n "__fish_use_subcommand" -a test      -d "Test deploy (no backup, keep monitor.kdl)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a greeter   -d "Noctalia Greeter (install|status|uninstall)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a fcitx     -d "NyxMellow fcitx5 skin (install|status|uninstall)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a update    -d "Update repo & configs (--force)"
complete -c nyxniri -f -n "__fish_use_subcommand" -a help      -d "Show help"

# install 子参数
complete -c nyxniri -f -n "__fish_seen_subcommand_from install deploy" -a full   -d "Full setup (deps + configs + optional)"
complete -c nyxniri -f -n "__fish_seen_subcommand_from install deploy" -a config -d "Configs only"

# theme 子参数
complete -c nyxniri -f -n "__fish_seen_subcommand_from theme" -a toggle -d "Toggle between dark and light"
complete -c nyxniri -f -n "__fish_seen_subcommand_from theme" -a dark   -d "Switch to dark theme"
complete -c nyxniri -f -n "__fish_seen_subcommand_from theme" -a light  -d "Switch to light theme"
complete -c nyxniri -f -n "__fish_seen_subcommand_from theme" -a sync   -d "Sync theme to current Noctalia mode"
complete -c nyxniri -f -n "__fish_seen_subcommand_from theme" -a status -d "Show current theme scheme & mode"

# snapshot 子参数
complete -c nyxniri -f -n "__fish_seen_subcommand_from snapshot backup" -a delete -d "Delete a snapshot"

# greeter / fcitx 子参数
complete -c nyxniri -f -n "__fish_seen_subcommand_from greeter" -a install   -d "Install & configure Greeter"
complete -c nyxniri -f -n "__fish_seen_subcommand_from greeter" -a status    -d "Show Greeter status"
complete -c nyxniri -f -n "__fish_seen_subcommand_from greeter" -a uninstall -d "Uninstall Greeter config"
complete -c nyxniri -f -n "__fish_seen_subcommand_from fcitx" -a install   -d "Install NyxMellow skin"
complete -c nyxniri -f -n "__fish_seen_subcommand_from fcitx" -a status    -d "Show skin status"
complete -c nyxniri -f -n "__fish_seen_subcommand_from fcitx" -a uninstall -d "Uninstall skin"

# update 参数
complete -c nyxniri -f -n "__fish_seen_subcommand_from update" -l force -d "Update and redeploy configs with a snapshot"
complete -c nyxniri -f -n "__fish_seen_subcommand_from update" -l no-deploy -d "Update source only"

# 快照序号动态补全 (rollback / snapshot delete)
function __nyxniri_snapshot_indices
    set -l dirs
    if test -d "$HOME/.config/NyxNiri/backups"
        for d in "$HOME/.config/NyxNiri/backups"/*
            switch (basename "$d")
                case 'snapshot_*' 'pre_rollback_*'
                    test -d "$d"; and set -a dirs "$d"
            end
        end
    end
    for d in "$HOME/.config"/dotfiles_backup_*
        test -d "$d"; and set -a dirs "$d"
    end
    set -l i 0
    for d in $dirs
        set i (math $i + 1)
        echo "$i"
    end
end
complete -c nyxniri -f -n "__fish_seen_subcommand_from rollback" -a "(__nyxniri_snapshot_indices)" -d "Snapshot index"
complete -c nyxniri -f -n "__fish_seen_subcommand_from delete" -a "(__nyxniri_snapshot_indices)" -d "Snapshot index"
