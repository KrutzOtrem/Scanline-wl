import json
import os
import subprocess
import sys
from dataclasses import dataclass

from .config import OverlayConfig
from .paths import LAYER_SHELL_LIB


# this module is the visual part of the app.


def ensure_layer_shell_preloaded() -> None:
    # gtk layer shell only works reliably here if the helper library is preloaded
    # before gi imports happen, so we handle that up front and re-exec ourselves.
    if os.environ.get("GTK4_LAYER_SHELL_PRELOADED") == "1" or not LAYER_SHELL_LIB:
        return

    current_preload = os.environ.get("LD_PRELOAD", "")
    preload_parts = [part for part in current_preload.split(":") if part]
    layer_shell_path = str(LAYER_SHELL_LIB)
    if layer_shell_path in preload_parts:
        return

    env = os.environ.copy()
    env["LD_PRELOAD"] = ":".join([layer_shell_path, *preload_parts])
    env["GTK4_LAYER_SHELL_PRELOADED"] = "1"
    os.execvpe(sys.executable, [sys.executable, *sys.argv], env)


ensure_layer_shell_preloaded()

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, Gio, Gtk, Gtk4LayerShell  # noqa: E402


@dataclass(frozen=True)
class MonitorInsets:
    # these come from the compositor, not from user config.
    # they describe reserved space around a monitor.
    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0


# this css is a small but important safety net against gtk drawing an opaque
# background where we only want transparent overlay content.
CSS = b"""
window,
#scanline-wl-window,
#scanline-drawing-area {
  background: transparent;
  background-color: transparent;
  box-shadow: none;
}
"""


class ScanlineWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        monitor: Gdk.Monitor,
        config: OverlayConfig,
        insets: MonitorInsets,
    ):
        super().__init__(application=app, title="Scanline WL")
        self.config = config

        # the layer surface needs to cover the physical monitor plus any
        # compositor-reserved edges we are intentionally canceling out.
        geometry = monitor.get_geometry()
        window_width = geometry.width + insets.left + insets.right
        window_height = geometry.height + insets.top + insets.bottom

        self.set_name("scanline-wl-window")
        self.set_decorated(False)
        self.set_focusable(False)
        self.set_can_focus(False)
        self.set_resizable(False)
        self.set_can_target(False)
        self.set_default_size(window_width, window_height)
        self.set_size_request(window_width, window_height)

        # layer-shell is what turns this into a desktop overlay rather than a
        # normal managed application window.
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_namespace(self, "scanline-wl")
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_monitor(self, monitor)

        # anchoring every edge gives us a fullscreen overlay surface on each monitor.
        for edge in (
            Gtk4LayerShell.Edge.TOP,
            Gtk4LayerShell.Edge.BOTTOM,
            Gtk4LayerShell.Edge.LEFT,
            Gtk4LayerShell.Edge.RIGHT,
        ):
            Gtk4LayerShell.set_anchor(self, edge, True)

        Gtk4LayerShell.set_exclusive_zone(self, 0)
        # hyprland reserves space for bars/panels; we negate that here so the
        # scanline mask still reaches the true screen bounds.
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, -insets.top)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, -insets.bottom)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.LEFT, -insets.left)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, -insets.right)

        area = Gtk.DrawingArea()
        area.set_name("scanline-drawing-area")
        # gtk was happy to give us only a partial drawing region until we
        # started forcing the content size explicitly.
        area.set_content_width(window_width)
        area.set_content_height(window_height)
        area.set_hexpand(True)
        area.set_vexpand(True)
        area.set_halign(Gtk.Align.FILL)
        area.set_valign(Gtk.Align.FILL)
        area.set_can_target(False)
        area.set_draw_func(self.on_draw)
        self.set_child(area)

        self.connect("map", self.on_map)

    def on_map(self, *_args):
        # an empty input region makes the overlay click-through.
        surface = self.get_surface()
        if surface is not None:
            surface.set_input_region(cairo.Region())

    def on_draw(self, _area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int):
        # start by clearing the full surface so only the scanline pattern remains.
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        spacing = max(1, self.config.spacing)
        thickness = max(1, min(self.config.thickness, spacing))

        if self.config.darkness > 0:
            # the main mask is just repeated dark horizontal bands.
            cr.set_source_rgba(0, 0, 0, self.config.darkness)
            for y in range(0, height, spacing):
                cr.rectangle(0, y, width, thickness)
            cr.fill()

        if self.config.glow > 0:
            # a faint light line under each dark band softens the effect a bit.
            cr.set_source_rgba(1, 1, 1, self.config.glow)
            for y in range(0, height, spacing):
                glow_y = y + thickness
                if glow_y >= height:
                    continue
                cr.rectangle(0, glow_y, width, 1)
            cr.fill()


class ScanlineApplication(Gtk.Application):
    def __init__(self, config: OverlayConfig):
        super().__init__(
            application_id="dev.krutzotrem.ScanlineWl",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.config = config
        self.windows_by_monitor: list[ScanlineWindow] = []
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(CSS)
        self.insets_by_geometry = load_hyprland_insets()

    def do_activate(self):
        # if gtk re-activates us, just present the existing overlay windows.
        if self.windows_by_monitor:
            for window in self.windows_by_monitor:
                window.present()
            return

        display = Gdk.Display.get_default()
        if display is None:
            print("No display available.", file=sys.stderr)
            self.quit()
            return

        Gtk.StyleContext.add_provider_for_display(
            display,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        monitors = display.get_monitors()
        total = monitors.get_n_items()
        if total == 0:
            print("No monitors detected.", file=sys.stderr)
            self.quit()
            return

        # create one overlay window per monitor so mixed-size multi-monitor
        # setups behave predictably.
        for index in range(total):
            monitor = monitors.get_item(index)
            window = ScanlineWindow(
                self,
                monitor,
                self.config,
                self.insets_by_geometry.get(monitor_geometry_key(monitor), MonitorInsets()),
            )
            self.windows_by_monitor.append(window)
            window.present()


def monitor_geometry_key(monitor: Gdk.Monitor) -> tuple[int, int, int, int]:
    # gtk monitors and hyprland monitor json do not share object identity,
    # so geometry is the practical common key.
    geometry = monitor.get_geometry()
    return (geometry.x, geometry.y, geometry.width, geometry.height)


def load_hyprland_insets() -> dict[tuple[int, int, int, int], MonitorInsets]:
    # hyprland tells us how much space bars/panels reserve on each monitor.
    # we use that to stretch the overlay back to the real screen edges.
    try:
        result = subprocess.run(
            ["hyprctl", "-j", "monitors"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        # if hyprctl is unavailable, we still run, just without inset compensation.
        return {}

    insets_by_geometry: dict[tuple[int, int, int, int], MonitorInsets] = {}
    for monitor in data:
        reserved = monitor.get("reserved", [0, 0, 0, 0])
        if len(reserved) != 4:
            reserved = [0, 0, 0, 0]

        key = (
            int(monitor.get("x", 0)),
            int(monitor.get("y", 0)),
            int(monitor.get("width", 0)),
            int(monitor.get("height", 0)),
        )
        # hyprland's reserved array is ordered as left, top, right, bottom.
        insets_by_geometry[key] = MonitorInsets(
            left=max(0, int(reserved[0])),
            top=max(0, int(reserved[1])),
            right=max(0, int(reserved[2])),
            bottom=max(0, int(reserved[3])),
        )

    return insets_by_geometry
