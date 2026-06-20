# Niri & Kitty Dotfiles

My personal desktop configurations featuring Niri scroll-able-tiling window manager, Kitty terminal emulator, and custom wallpapers.

## 📂 Repository Structure

- **[niri/](./niri/)**: Config files for [Niri](https://github.com/YaLTeR/niri). Includes the custom `dms` configuration splits for cleaner management (binds, layout, window rules, etc.).
- **[kitty/](./kitty/)**: Config files for [Kitty](https://sw.kovidgoyal.net/kitty/) terminal, containing custom theme setups (e.g., Dank theme, Matugen integration).
- **[wallpapers/](./wallpapers/)**: A collection of high-quality wallpapers used in this desktop setup.

## 🚀 Getting Started

If you want to use these configurations, you can clone the repository and symlink them to your `.config` directory:

```bash
# Clone the repository
git clone https://github.com/your-username/niri-kitty-dotfiles.git ~/项目/dotfiles

# Backup your existing configs
mv ~/.config/niri ~/.config/niri.bak
mv ~/.config/kitty ~/.config/kitty.bak

# Create symlinks
ln -s ~/项目/dotfiles/niri ~/.config/niri
ln -s ~/项目/dotfiles/kitty ~/.config/kitty
```

*Note: For wallpapers, place them or symlink them to your preferred wallpaper directory (e.g., `~/图片/wallpapers`).*

## 🎨 Preview & Highlights

- **WM**: Niri Window Manager
- **Terminal**: Kitty
- **Features**: Structured modular Niri configs under `niri/dms`, automatic theme options.
