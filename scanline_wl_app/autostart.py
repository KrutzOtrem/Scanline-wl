from .paths import AUTOSTART_DIR, AUTOSTART_FILE, LAUNCH_SCRIPT


# all we really need is the ability to write or remove one standard desktop entry.


def is_autostart_enabled() -> bool:
    return AUTOSTART_FILE.exists()


def set_autostart_enabled(enabled: bool) -> None:
    # enabling writes the user-local autostart file; disabling removes it.
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(_desktop_entry(), encoding="utf-8")
        return

    try:
        AUTOSTART_FILE.unlink()
    except FileNotFoundError:
        pass


def _desktop_entry() -> str:
    # start the overlay directly on login using the saved config profile.
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=Scanline WL",
            "Comment=Start the scanline overlay on login",
            f"Exec=python3 {LAUNCH_SCRIPT}",
            "Terminal=false",
            "Categories=Graphics;Utility;",
            "X-GNOME-Autostart-enabled=true",
            "",
        ]
    )
