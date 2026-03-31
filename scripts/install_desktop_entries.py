#!/usr/bin/env python3

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_SCRIPT = PROJECT_ROOT / "scanline_wl.py"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"


def desktop_entry(name: str, comment: str, args: str, categories: str) -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            f"Name={name}",
            f"Comment={comment}",
            f"Exec=python3 {LAUNCH_SCRIPT} {args}".rstrip(),
            "Terminal=false",
            f"Categories={categories}",
            "StartupNotify=false",
            "",
        ]
    )


def main() -> int:
    APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

    entries = {
        "scanline-wl.desktop": desktop_entry(
            "Scanline WL",
            "Toggle the desktop scanline overlay",
            "--toggle",
            "Graphics;Utility;",
        ),
        "scanline-wl-settings.desktop": desktop_entry(
            "Scanline WL Settings",
            "Adjust scanline overlay intensity and behavior",
            "--settings",
            "Graphics;Utility;Settings;",
        ),
    }

    for filename, content in entries.items():
        path = APPLICATIONS_DIR / filename
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path}")

    try:
        subprocess.run(
            ["update-desktop-database", str(APPLICATIONS_DIR)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
