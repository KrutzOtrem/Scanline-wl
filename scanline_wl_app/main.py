import argparse
import os
import sys

from .config import OverlayConfig, PRESETS, clamp_config, load_saved_config
from .control import claim_pidfile, read_pidfile, stop_running_instance


# this file is the traffic cop for the whole app.
# it decides whether the current run should become the overlay itself,
# the settings window, or a control action like stop/toggle.


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone Wayland scanline overlay.")
    parser.add_argument("--preset", choices=sorted(PRESETS))
    parser.add_argument("--spacing", type=int, help="Pixels between scanline starts.")
    parser.add_argument("--thickness", type=int, help="Dark scanline thickness in pixels.")
    parser.add_argument("--darkness", type=float, help="Dark line opacity from 0.0 to 1.0.")
    parser.add_argument("--glow", type=float, help="Soft light line opacity from 0.0 to 1.0.")
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Open the settings window instead of the overlay.",
    )
    parser.add_argument(
        "--toggle",
        action="store_true",
        help="If already running, stop the overlay. Otherwise start it.",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the running overlay and exit.",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Fail instead of replacing an existing overlay instance.",
    )
    args = parser.parse_args()

    # start from the saved profile, then let preset/cli flags override pieces of it.
    config = load_saved_config()
    if args.preset in PRESETS:
        # presets replace the saved profile first, and then the more specific
        # cli flags can still tweak individual values after that.
        config = PRESETS[args.preset]
    if args.spacing is not None:
        config = OverlayConfig(args.spacing, config.thickness, config.darkness, config.glow)
    if args.thickness is not None:
        config = OverlayConfig(config.spacing, args.thickness, config.darkness, config.glow)
    if args.darkness is not None:
        config = OverlayConfig(config.spacing, config.thickness, args.darkness, config.glow)
    if args.glow is not None:
        config = OverlayConfig(config.spacing, config.thickness, config.darkness, args.glow)

    args.config = clamp_config(config)
    return args


def main() -> int:
    if os.environ.get("XDG_SESSION_TYPE", "").lower() not in {"wayland", ""}:
        print("This app targets wayland layer-shell compositors.", file=sys.stderr)

    args = parse_args()

    # settings mode is a separate gtk app on purpose so it can manage the
    # overlay process without being the overlay process.
    if args.settings:
        from .settings import SettingsApplication

        return SettingsApplication(args.config).run([sys.argv[0]])

    if args.stop:
        # stop mode is intentionally just a control action, not a new app instance.
        stop_running_instance()
        return 0

    running_pid = read_pidfile()
    if args.toggle and running_pid is not None:
        # toggle means "if something is already running, turn it off and stop here".
        stop_running_instance()
        return 0

    if running_pid is not None:
        if args.no_replace:
            print(f"scanline-wl is already running (pid {running_pid}).", file=sys.stderr)
            return 1
        stop_running_instance()

    # from here down we are becoming the live overlay instance.
    claim_pidfile()

    from .overlay import ScanlineApplication

    return ScanlineApplication(args.config).run([sys.argv[0]])
