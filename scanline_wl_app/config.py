import json
from dataclasses import dataclass

from .paths import CONFIG_DIR, CONFIG_FILE


@dataclass(frozen=True)
class OverlayConfig:
    # this is the shared config shape used everywhere in the app.
    # keeping it as one dataclass makes it easier to pass around and reason about.
    spacing: int
    thickness: int
    darkness: float
    glow: float


# these are convenience starting points, not hardcoded modes hidden inside the renderer.
PRESETS = {
    "subtle": OverlayConfig(spacing=2, thickness=1, darkness=0.075, glow=0.02),
    "medium": OverlayConfig(spacing=2, thickness=2, darkness=0.12, glow=0.03),
    "strong": OverlayConfig(spacing=3, thickness=2, darkness=0.14, glow=0.037),
}

DEFAULT_PRESET = "medium"


def clamp_config(config: OverlayConfig) -> OverlayConfig:
    # keep all externally supplied values in the ranges the renderer expects.
    return OverlayConfig(
        spacing=max(1, int(config.spacing)),
        thickness=max(1, int(config.thickness)),
        darkness=min(max(0.0, float(config.darkness)), 1.0),
        glow=min(max(0.0, float(config.glow)), 1.0),
    )


def config_to_dict(config: OverlayConfig) -> dict[str, float | int]:
    # the saved file is intentionally simple enough that a user can edit it by hand.
    return {
        "spacing": config.spacing,
        "thickness": config.thickness,
        "darkness": config.darkness,
        "glow": config.glow,
    }


def load_saved_config() -> OverlayConfig:
    # the saved profile is the normal default when no preset/flags override it.
    try:
        with CONFIG_FILE.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return PRESETS[DEFAULT_PRESET]

    try:
        # if the saved file is malformed, we recover by falling back instead of
        # failing startup over one broken local file.
        config = OverlayConfig(
            spacing=int(data["spacing"]),
            thickness=int(data["thickness"]),
            darkness=float(data["darkness"]),
            glow=float(data["glow"]),
        )
    except (KeyError, TypeError, ValueError):
        return PRESETS[DEFAULT_PRESET]

    return clamp_config(config)


def save_config(config: OverlayConfig) -> None:
    # save a clean, clamped profile so later launches do not inherit junk values.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as handle:
        json.dump(config_to_dict(clamp_config(config)), handle, indent=2)
        handle.write("\n")
