from pathlib import Path

APP_ID = "scanline-wl"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_SCRIPT = PROJECT_ROOT / "scanline_wl.py"
LAYER_SHELL_LIB = Path("/usr/lib/libgtk4-layer-shell.so")
STATE_DIR = Path.home() / ".cache" / APP_ID
PIDFILE = STATE_DIR / f"{APP_ID}.pid"
CONFIG_DIR = Path.home() / ".config" / APP_ID
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_ID}.desktop"
