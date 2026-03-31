import atexit
import os
import signal
import subprocess
import sys
import time

from .paths import LAUNCH_SCRIPT, PIDFILE, STATE_DIR


# this module keeps process-control behavior in one place.
# the rest of the app can ask for "start", "stop", or "replace" without caring
# how pidfiles or detached launches work.


def process_alive(pid: int) -> bool:
    # signal 0 is the cheap "does this pid exist" check.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def remove_pidfile() -> None:
    # pidfile cleanup is best-effort; shutdown should not fail if the file is already gone.
    try:
        PIDFILE.unlink()
    except (FileNotFoundError, OSError):
        pass


def read_pidfile() -> int | None:
    # this lets the settings window and cli control the live overlay process.
    try:
        value = PIDFILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

    if not value:
        return None

    try:
        pid = int(value)
    except ValueError:
        remove_pidfile()
        return None

    if process_alive(pid):
        return pid

    remove_pidfile()
    return None


def wait_for_exit(pid: int, timeout_seconds: float = 2.0) -> bool:
    # replacing the overlay is more reliable if we wait for teardown explicitly.
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return True
        time.sleep(0.05)
    return not process_alive(pid)


def stop_running_instance(timeout_seconds: float = 2.0) -> bool:
    # this is the low-level stop path used by the main entrypoint.
    pid = read_pidfile()
    if pid is None or pid == os.getpid():
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        remove_pidfile()
        return False

    if wait_for_exit(pid, timeout_seconds):
        remove_pidfile()
        return True

    raise RuntimeError(f"Timed out waiting for scanline-wl (pid {pid}) to exit.")


def claim_pidfile() -> None:
    # the overlay process owns the pidfile for as long as it is the active instance.
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    atexit.register(remove_pidfile)


def script_command(*args: str) -> list[str]:
    # always re-run the project launcher so external tools only need one entrypoint.
    return [sys.executable, str(LAUNCH_SCRIPT), *args]


def launch_overlay_process() -> None:
    # spawn a detached replacement so the settings window can keep running.
    subprocess.Popen(
        script_command(),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_overlay_process() -> None:
    # this wrapper is mostly for the settings window, where "stop the overlay"
    # is clearer than re-implementing pidfile logic in ui code.
    subprocess.run(
        script_command("--stop"),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def replace_overlay_process() -> None:
    # stopping first avoids the flaky "first click kills, second click starts" race.
    stop_overlay_process()
    time.sleep(0.15)
    launch_overlay_process()
