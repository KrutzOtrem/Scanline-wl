# Scanline WL

`scanline-wl` is a small standalone Linux desktop overlay app that draws a CRT-like scanline mask over the whole Wayland desktop.

It is intentionally simple:
- one transparent click-through overlay per monitor
- layer-shell based, so it sits above normal windows
- preset-based tuning for subtle or stronger pixel-art looks

## Requirements

- Wayland compositor with layer-shell support
- GTK4
- gtk4-layer-shell
- Python 3 with PyGObject and Cairo

## Install Dependencies

This app targets Wayland compositors that support layer-shell.
In practice, the safest target is a wlroots-style setup such as Hyprland or Sway.

Install the runtime dependencies first:

### arch linux

```bash
sudo pacman -S --needed python python-gobject python-cairo gtk4 gtk4-layer-shell
```

### fedora

```bash
sudo dnf install python3 python3-gobject python3-cairo gtk4 gtk4-layer-shell
```

### debian testing / unstable

```bash
sudo apt install python3 python3-gi python3-cairo gir1.2-gtk-4.0 gir1.2-gtk4layershell-1.0
```

### ubuntu / other desktops

Ubuntu package availability for `gtk4-layer-shell` is less consistent than Arch or Fedora, and plain "Wayland" is not enough by itself.
If your compositor or distro does not provide the GTK4 layer-shell introspection package, this app will not run until that dependency is available.

## Run

From the project root:

```bash
python3 scanline_wl.py
```

Launching it again will now replace the previous instance instead of stacking another fullscreen layer on top.

Try presets:

```bash
python3 scanline_wl.py --preset subtle
python3 scanline_wl.py --preset medium
python3 scanline_wl.py --preset strong
```

Toggle the overlay on or off:

```bash
python3 scanline_wl.py --toggle
```

Open the settings window:

```bash
python3 scanline_wl.py --settings
```

Stop a running instance explicitly:

```bash
python3 scanline_wl.py --stop
```

## Stop And Uninstall

If the overlay is running and you want it gone immediately:

```bash
python3 scanline_wl.py --stop
```

If you enabled `start on login`, either disable it in the settings window or remove the autostart file manually:

```bash
rm -f ~/.config/autostart/scanline-wl.desktop
```

To remove your saved settings and cached runtime state:

```bash
rm -rf ~/.config/scanline-wl ~/.cache/scanline-wl
```

If you installed launcher entries into your app menu:

```bash
rm -f ~/.local/share/applications/scanline-wl.desktop \
  ~/.local/share/applications/scanline-wl-settings.desktop
```

If you cloned the repo just for this app, you can then delete the project folder too.

Or tune manually:

```bash
python3 scanline_wl.py \
  --spacing 3 \
  --thickness 2 \
  --darkness 0.14 \
  --glow 0.037
```

## install app launchers

To install launcher entries that show up in your desktop app menu:

```bash
python3 scripts/install_desktop_entries.py
```

This writes user-local `.desktop` files into `~/.local/share/applications` with the correct absolute path for your clone.

## source layout

- `scanline_wl.py`: tiny launcher shim so commands and desktop entries stay stable
- `scanline_wl_app/main.py`: cli parsing and mode routing
- `scanline_wl_app/config.py`: presets and saved config handling
- `scanline_wl_app/control.py`: pidfile and start/stop/replace logic
- `scanline_wl_app/overlay.py`: the actual wayland layer-shell overlay
- `scanline_wl_app/settings.py`: the gtk settings window
- `scanline_wl_app/autostart.py`: login autostart entry management
- `scanline_wl_app/paths.py`: shared filesystem paths

## Notes

- The current MVP targets Wayland first.
- Saved settings live at `~/.config/scanline-wl/config.json`.
- Login autostart is managed through `~/.config/autostart/scanline-wl.desktop`.
- The settings window can save, apply, start/replace, and stop the overlay.
- The repo `.desktop` files are templates; the installer script writes real local launchers with your actual path.
