import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from .autostart import is_autostart_enabled, set_autostart_enabled
from .config import PRESETS, OverlayConfig, clamp_config, save_config
from .control import replace_overlay_process, stop_overlay_process


# this window is deliberately small and direct.
# it is not trying to be a huge preferences dialog, just a friendly control
# panel for the few settings that actually matter to this app.


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, initial_config: OverlayConfig):
        super().__init__(application=app, title="Scanline WL Settings")
        self.set_default_size(440, 380)
        self.set_resizable(False)

        # these ranges match the values the overlay renderer is designed for.
        self.spacing_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 8, 1)
        self.thickness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 4, 1)
        self.darkness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 0.4, 0.005)
        self.glow_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 0.15, 0.0025)
        self.autostart_check = Gtk.CheckButton()
        self.status_label = Gtk.Label(xalign=0.5)
        self.status_label.set_halign(Gtk.Align.CENTER)

        for scale, digits in (
            (self.spacing_scale, 0),
            (self.thickness_scale, 0),
            (self.darkness_scale, 3),
            (self.glow_scale, 3),
        ):
            self._setup_scale(scale, digits)

        # the layout here is built by hand so the controls stay visually centered
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_halign(Gtk.Align.CENTER)
        content.set_valign(Gtk.Align.CENTER)

        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        presets_box.set_halign(Gtk.Align.CENTER)
        for preset_name in ("subtle", "medium", "strong"):
            button = Gtk.Button(label=preset_name.title())
            button.connect("clicked", self.on_preset_clicked, preset_name)
            presets_box.append(button)

        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        controls.set_halign(Gtk.Align.CENTER)
        rows = (
            ("Spacing", self.spacing_scale, 0),
            ("Thickness", self.thickness_scale, 1),
            ("Darkness", self.darkness_scale, 2),
            ("Glow", self.glow_scale, 3),
        )
        for label_text, scale, _row in rows:
            # each manual control row is a pair: fixed-width label and one slider.
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row_box.set_halign(Gtk.Align.CENTER)
            row_box.set_valign(Gtk.Align.CENTER)
            row_box.append(self._row_label(label_text))
            row_box.append(scale)
            controls.append(row_box)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_halign(Gtk.Align.CENTER)
        for label, handler in (
            ("Save", self.on_save_clicked),
            ("Apply", self.on_apply_clicked),
            ("Start / Replace", self.on_start_clicked),
            ("Stop", self.on_stop_clicked),
        ):
            button = Gtk.Button(label=label)
            button.connect("clicked", handler)
            actions.append(button)

        presets_label = self._section_label("Presets")
        manual_label = self._section_label("Manual")
        manual_label.set_margin_top(12)

        startup_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        startup_row.set_halign(Gtk.Align.CENTER)
        startup_row.set_margin_top(8)
        startup_label = self._section_label("start on login")

        # splitting the checkbox from the label gives us more control over placement.
        startup_row.append(self.autostart_check)
        startup_row.append(startup_label)

        content.append(presets_label)
        content.append(presets_box)
        content.append(manual_label)
        content.append(controls)
        content.append(startup_row)
        content.append(actions)
        content.append(self.status_label)

        self.set_child(content)
        self.load_into_controls(initial_config)
        self.autostart_check.set_active(is_autostart_enabled())
        self.autostart_check.connect("toggled", self.on_autostart_toggled)
        self.set_status("Loaded current profile.")

    def _setup_scale(self, scale: Gtk.Scale, digits: int) -> None:
        scale.set_draw_value(True)
        scale.set_digits(digits)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_size_request(220, -1)
        scale.set_valign(Gtk.Align.CENTER)
        scale.set_halign(Gtk.Align.FILL)

    def _row_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=1.0)
        label.set_halign(Gtk.Align.END)
        label.set_valign(Gtk.Align.CENTER)
        label.set_size_request(92, -1)
        return label

    def _section_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0.5)
        label.set_halign(Gtk.Align.CENTER)
        label.add_css_class("heading")
        return label

    def set_status(self, text: str) -> None:
        # a single inline status message is enough for this tool and avoids popups.
        self.status_label.set_label(text)

    def current_config(self) -> OverlayConfig:
        # read the current ui state back into a clean config object.
        return clamp_config(
            OverlayConfig(
                spacing=int(round(self.spacing_scale.get_value())),
                thickness=int(round(self.thickness_scale.get_value())),
                darkness=self.darkness_scale.get_value(),
                glow=self.glow_scale.get_value(),
            )
        )

    def load_into_controls(self, config: OverlayConfig) -> None:
        # the opposite of current_config(): push app state into the visible widgets.
        self.spacing_scale.set_value(config.spacing)
        self.thickness_scale.set_value(config.thickness)
        self.darkness_scale.set_value(config.darkness)
        self.glow_scale.set_value(config.glow)

    def on_preset_clicked(self, _button: Gtk.Button, preset_name: str) -> None:
        # presets are just convenience loads into the live controls.
        self.load_into_controls(PRESETS[preset_name])
        self.set_status(f"Loaded {preset_name} preset.")

    def on_save_clicked(self, _button: Gtk.Button) -> None:
        save_config(self.current_config())
        self.set_status("Saved profile.")

    def on_apply_clicked(self, _button: Gtk.Button) -> None:
        save_config(self.current_config())
        # apply should update the live overlay immediately, not just the saved profile.
        replace_overlay_process()
        self.set_status("Saved and applied.")

    def on_start_clicked(self, _button: Gtk.Button) -> None:
        # start/replace also saves first, because users expect the thing they are
        # currently seeing in the ui to be the thing that launches.
        save_config(self.current_config())
        replace_overlay_process()
        self.set_status("Overlay started or replaced.")

    def on_stop_clicked(self, _button: Gtk.Button) -> None:
        stop_overlay_process()
        self.set_status("Overlay stopped.")

    def on_autostart_toggled(self, button: Gtk.CheckButton) -> None:
        enabled = button.get_active()
        set_autostart_enabled(enabled)
        if enabled:
            self.set_status("Autostart enabled.")
        else:
            self.set_status("Autostart disabled.")


class SettingsApplication(Gtk.Application):
    def __init__(self, initial_config: OverlayConfig):
        super().__init__(
            application_id="dev.krutzotrem.ScanlineWl.Settings",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        # the entrypoint resolves the config first and hands it to the window here.
        self.initial_config = initial_config

    def do_activate(self):
        SettingsWindow(self, self.initial_config).present()
