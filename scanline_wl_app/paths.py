import os
from ctypes.util import find_library
from pathlib import Path


def resolve_layer_shell_lib() -> str | None:
    # allow manual override first for debugging or unusual distro layouts.
    env_path = os.environ.get("GTK4_LAYER_SHELL_LIB")
    if env_path:
        return env_path

    # this is the most portable path because it asks the system linker.
    soname = find_library("gtk4-layer-shell")
    if soname:
        return soname

    # keep common fallback locations for systems where find_library is thin.
    for candidate in (
        "/usr/lib/libgtk4-layer-shell.so",
        "/usr/lib64/libgtk4-layer-shell.so",
        "/usr/lib/x86_64-linux-gnu/libgtk4-layer-shell.so",
        "/usr/lib/aarch64-linux-gnu/libgtk4-layer-shell.so",
    ):
        if Path(candidate).exists():
            return candidate

    return None

APP_ID = "scanline-wl"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_SCRIPT = PROJECT_ROOT / "scanline_wl.py"
LAYER_SHELL_LIB = resolve_layer_shell_lib()
STATE_DIR = Path.home() / ".cache" / APP_ID
PIDFILE = STATE_DIR / f"{APP_ID}.pid"
CONFIG_DIR = Path.home() / ".config" / APP_ID
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_ID}.desktop"
