#!/usr/bin/python
"""Reusable Omarchy tablet sleep, audio, power-profile, and agent-awake policy."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def command(*args):
    return subprocess.check_output(args, text=True, timeout=8).strip()


def is_external_stream(stream):
    properties = stream.get("properties", {})
    identity = " ".join(str(properties.get(key, "")) for key in
                        ("application.id", "application.name", "application.process.binary", "node.name"))
    return not stream.get("corked", True) and "easyeffects" not in identity.lower() and "easy effects" not in identity.lower()


class Policy:
    def __init__(self):
        self.locked_since = None
        self.last_audio = None
        self.last_attempt = None

    def action(self, state, now):
        # Failed probes never mean idle. Start a fresh interval after activity,
        # inhibition, startup, or resume rather than sleeping immediately.
        if not state["locked"] or not state["screen_off"] or state["awake"] or state["inhibited"]:
            self.locked_since = None
            return None
        if state["audio"]:
            self.last_audio = now
            self.locked_since = None
            return None
        if self.last_audio is not None and now - self.last_audio < 60:
            self.locked_since = None
            return None
        if self.locked_since is None:
            self.locked_since = now
        delay = 300 if state["ac"] else 60
        if now - self.locked_since < delay:
            return None
        if self.last_attempt is not None and now - self.last_attempt < 300:
            return None
        self.last_attempt = now
        self.locked_since = None
        # At low charge save to disk immediately rather than spending the
        # remaining reserve in s2idle. UPower separately protects active use.
        return "hibernate" if not state["ac"] and state["capacity"] <= 10 else "suspend-then-hibernate"


def power_state():
    supplies = list(Path("/sys/class/power_supply").iterdir())
    batteries = [p for p in supplies if (p / "type").read_text().strip() == "Battery" and (p / "capacity").exists()]
    if not batteries:
        raise RuntimeError("No battery capacity available")
    battery = next((p for p in batteries if p.name == "BAT0"), batteries[0])
    ac = any((p / "online").exists() and (p / "online").read_text().strip() == "1"
             for p in supplies if (p / "type").read_text().strip() != "Battery")
    return ac, int((battery / "capacity").read_text())


def audio_playing():
    streams = json.loads(command("pactl", "-f", "json", "list", "sink-inputs"))
    streams += json.loads(command("pactl", "-f", "json", "list", "source-outputs"))
    return any(is_external_stream(stream) for stream in streams)


def cover_inhibitor():
    """Retain tablet cover behavior, excluding EasyEffects' internal streams."""
    inhibitor = None
    last_audio = None
    stay_awake = Path.home() / '.local/state/omarchy/indicators/stay-awake'
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while True:
            try:
                keep_awake = stay_awake.exists()
                if not keep_awake and audio_playing():
                    last_audio = time.monotonic()
                keep_awake = keep_awake or (last_audio is not None and time.monotonic() - last_audio < 60)
            except (OSError, ValueError, subprocess.SubprocessError):
                # Unknown audio state: defer a lid-triggered sleep this cycle.
                keep_awake = True
            if keep_awake and (inhibitor is None or inhibitor.poll() is not None):
                inhibitor = subprocess.Popen([
                    'systemd-inhibit', '--what=handle-lid-switch', '--mode=block',
                    '--who=Dell tablet', '--why=Stay Awake or real playback/recording', 'sleep', 'infinity'])
            elif not keep_awake and inhibitor is not None:
                inhibitor.terminate()
                inhibitor.wait(timeout=5)
                inhibitor = None
            time.sleep(5)
    finally:
        if inhibitor is not None and inhibitor.poll() is None:
            inhibitor.terminate()
            inhibitor.wait(timeout=5)


def snapshot(ac, capacity):
    lock = json.loads(command("omarchy-shell", "lock", "status"))
    if not isinstance(lock.get("secure"), bool):
        raise RuntimeError("Missing secure lock status")
    state = dict(ac=ac, capacity=capacity, locked=lock["secure"],
                 screen_off=False, awake=False, inhibited=False, audio=False)
    if not state["locked"]:
        return state
    monitors = json.loads(command("hyprctl", "monitors", "-j"))
    enabled = [monitor for monitor in monitors if not monitor.get("disabled", False)]
    if not enabled or any(not isinstance(monitor.get("dpmsStatus"), bool) for monitor in enabled):
        raise RuntimeError("Missing display power status")
    state["screen_off"] = all(not monitor["dpmsStatus"] for monitor in enabled)
    if not state["screen_off"]:
        return state
    idle = json.loads(command("omarchy-shell", "idle", "status"))
    if not isinstance(idle.get("stayAwake"), bool) or not idle.get("stayAwakeStateLoaded"):
        raise RuntimeError("Missing Stay Awake status")
    state["awake"] = idle["stayAwake"]
    if state["awake"]:
        return state
    inhibitors = json.loads(command("systemd-inhibit", "--list", "--json=short") or "[]")
    if not isinstance(inhibitors, list):
        raise RuntimeError("Unexpected inhibitor list")
    inhibited = any(item["mode"] in ("block", "block-weak") and
                    set(item["what"].split(":")) & {"idle", "sleep"} for item in inhibitors)
    state["inhibited"] = inhibited
    if not inhibited:
        state["audio"] = audio_playing()
    return state


def agent_working():
    # Short-lived local socket calls only: no process-tree scans or network.
    deadline = time.monotonic() + 2
    sessions = json.loads(subprocess.check_output(
        ['herdr', 'session', 'list', '--json'], text=True, timeout=2))
    for session in sessions['sessions']:
        if not session.get('running'):
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError('Agent status query timed out')
        environment = dict(os.environ, HERDR_SOCKET_PATH=session['socket_path'])
        agents = json.loads(subprocess.check_output(
            ['herdr', 'agent', 'list'], env=environment, text=True, timeout=remaining))
        if any(agent.get('agent_status') == 'working' for agent in agents['result']['agents']):
            return True
    return False


def owns_awake(marker, awake):
    if not marker.exists() or not awake.exists():
        return False
    identity = marker.read_text().strip()
    # Accept the old watcher's empty marker during migration.
    return not identity or identity == str(awake.stat().st_mtime_ns)


def agents_inhibitor():
    awake = Path.home() / '.local/state/omarchy/indicators/stay-awake'
    marker = Path(os.getenv('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'stay-awake-agents/auto'
    marker.parent.mkdir(parents=True, exist_ok=True)
    suppressed = False
    last_error = None

    def release():
        if owns_awake(marker, awake):
            command('omarchy-toggle-idle', 'allow-idle')
            print('Agents stopped: automatic Stay Awake released', flush=True)
        marker.unlink(missing_ok=True)

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while True:
            if marker.exists() and not awake.exists():
                marker.unlink()
                suppressed = True
            elif marker.exists() and not owns_awake(marker, awake):
                # A manual touch changed ownership: leave the manual choice on.
                marker.unlink()
            try:
                working = agent_working()
                last_error = None
            except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
                working = False
                if str(error) != last_error:
                    print(f'Agent status unavailable; releasing automatic Stay Awake: {error}', flush=True)
                    last_error = str(error)
            if not working:
                suppressed = False
                release()
            elif not suppressed and not awake.exists():
                ac, capacity = power_state()
                if ac or capacity > 10:
                    command('omarchy-toggle-idle', 'stay-awake')
                    marker.write_text(str(awake.stat().st_mtime_ns))
                    print('Agent working: automatic Stay Awake enabled', flush=True)
            # No completion grace: idle, waiting for input, exited, and crashed
            # agents release on this next lightweight five-second check.
            time.sleep(5)
    finally:
        release()


def main():
    policy = Policy()
    previous_ac = None
    last_error = None
    while True:
        try:
            ac, capacity = power_state()
            # Only set at startup or a power-source transition. Manual profile
            # choices remain in effect until the next transition.
            if ac != previous_ac:
                profile = "balanced" if ac else "power-saver"
                command("powerprofilesctl", "set", profile)
                previous_ac = ac
                print(f"Power source {'AC' if ac else 'battery'}: {profile}", flush=True)
            action = policy.action(snapshot(ac, capacity), time.monotonic())
            if action:
                # Recheck immediately before requesting sleep. systemctl also
                # respects logind sleep inhibitors and Omarchy locks via its
                # existing PrepareForSleep delay inhibitor.
                state = snapshot(*power_state())
                if state["locked"] and state["screen_off"] and not any(state[key] for key in ("awake", "audio", "inhibited")):
                    print(f"Locked and inactive: {action} (battery {state['capacity']}%)", flush=True)
                    subprocess.run(["systemctl", "--no-ask-password", action], check=True)
                policy.locked_since = None
            last_error = None
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
            policy.locked_since = None
            message = str(error)
            if message != last_error:
                print(f"Automatic sleep deferred: {message}", flush=True)
                last_error = message
        time.sleep(15)


if __name__ == "__main__":
    if sys.argv[1:] == ['--cover-inhibitor']:
        cover_inhibitor()
    elif sys.argv[1:] == ['--agents-inhibitor']:
        agents_inhibitor()
    else:
        main()
