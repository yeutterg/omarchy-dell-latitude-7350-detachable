#!/usr/bin/python
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
import tempfile
import contextlib
import io
sys.dont_write_bytecode = True

path = Path(__file__).resolve().parents[2] / 'home/.local/lib/tablet-power/manager.py'
loader = importlib.machinery.SourceFileLoader('dell_power', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class PolicyTests(unittest.TestCase):
    def state(self, **overrides):
        return dict(dict(locked=True, screen_off=True, awake=False, inhibited=False,
                         audio=False, ac=False, capacity=50), **overrides)

    def test_battery_and_ac_delay(self):
        for ac, delay in ((False, 60), (True, 300)):
            policy = module.Policy()
            self.assertIsNone(policy.action(self.state(ac=ac), 0))
            self.assertIsNone(policy.action(self.state(ac=ac), delay - 1))
            self.assertEqual(policy.action(self.state(ac=ac), delay), 'suspend-then-hibernate')

    def test_activity_and_inhibition_restart_interval(self):
        for change in (dict(locked=False), dict(screen_off=False), dict(awake=True),
                       dict(inhibited=True), dict(audio=True)):
            policy = module.Policy()
            policy.action(self.state(), 0)
            self.assertIsNone(policy.action(self.state(**change), 59))
            self.assertIsNone(policy.action(self.state(), 120))
            self.assertEqual(policy.action(self.state(), 180), 'suspend-then-hibernate')

    def test_low_battery_uses_disk_without_waiting_in_suspend(self):
        policy = module.Policy()
        policy.action(self.state(capacity=9), 0)
        self.assertEqual(policy.action(self.state(capacity=9), 60), 'hibernate')

    def test_failed_sleep_is_not_retried_every_poll(self):
        policy = module.Policy()
        policy.action(self.state(), 0)
        self.assertEqual(policy.action(self.state(), 60), 'suspend-then-hibernate')
        self.assertIsNone(policy.action(self.state(), 75))
        self.assertIsNone(policy.action(self.state(), 135))
        self.assertEqual(policy.action(self.state(), 360), 'suspend-then-hibernate')

    def test_processing_stream_does_not_keep_machine_awake(self):
        self.assertFalse(module.is_external_stream(dict(corked=False, properties={'application.name': 'Easy Effects'})))
        self.assertFalse(module.is_external_stream(dict(corked=False, properties={'application.process.binary': 'easyeffects'})))
        self.assertFalse(module.is_external_stream(dict(corked=True, properties={'application.name': 'Chromium'})))
        self.assertTrue(module.is_external_stream(dict(corked=False, properties={'application.name': 'Chromium'})))

    def test_snapshot_accepts_no_inhibitors_and_filters_processing(self):
        replies = {
            ('omarchy-shell', 'lock', 'status'): '{"secure":true,"locked":true}',
            ('omarchy-shell', 'idle', 'status'): '{"stayAwake":false,"stayAwakeStateLoaded":true}',
            ('systemd-inhibit', '--list', '--json=short'): '',
            ('pactl', '-f', 'json', 'list', 'sink-inputs'): '[{"corked":false,"properties":{"application.name":"Easy Effects"}}]',
            ('pactl', '-f', 'json', 'list', 'source-outputs'): '[]',
            ('hyprctl', 'monitors', '-j'): '[{"disabled":false,"dpmsStatus":false}]',
        }
        with patch.object(module, 'command', side_effect=lambda *args: replies[args]):
            state = module.snapshot(False, 50)
        self.assertFalse(state['audio'])
        self.assertFalse(state['inhibited'])
        self.assertTrue(state['screen_off'])
        replies[('systemd-inhibit', '--list', '--json=short')] = '[{"what":"idle:sleep","mode":"block"}]'
        with patch.object(module, 'command', side_effect=lambda *args: replies[args]):
            self.assertTrue(module.snapshot(False, 50)['inhibited'])

    def test_unknown_lock_status_does_not_mean_idle(self):
        with patch.object(module, 'command', return_value='{}'):
            with self.assertRaises(RuntimeError):
                module.snapshot(False, 50)

    def test_unlocked_probe_skips_expensive_queries(self):
        with patch.object(module, 'command', return_value='{"secure":false}') as probe:
            self.assertFalse(module.snapshot(False, 50)['locked'])
            probe.assert_called_once_with('omarchy-shell', 'lock', 'status')

    def test_awake_ownership_preserves_manual_toggle(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'auto'
            awake = Path(directory) / 'awake'
            awake.touch()
            marker.write_text(str(awake.stat().st_mtime_ns))
            self.assertTrue(module.owns_awake(marker, awake))
            # A user setting Stay Awake again refreshes the state identity.
            import os
            stamp = awake.stat().st_mtime_ns + 1000000000
            os.utime(awake, ns=(stamp, stamp))
            self.assertFalse(module.owns_awake(marker, awake))
            awake.unlink()
            self.assertFalse(module.owns_awake(marker, awake))

    def test_agent_completion_releases_on_next_poll_without_grace(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            awake = home / '.local/state/omarchy/indicators/stay-awake'
            awake.parent.mkdir(parents=True)
            calls = []

            def toggle(*args):
                calls.append(args)
                if args[-1] == 'stay-awake':
                    awake.touch()
                else:
                    awake.unlink(missing_ok=True)
                return ''

            with patch.object(module.Path, 'home', return_value=home), \
                 patch.dict(module.os.environ, {'XDG_STATE_HOME': str(home / '.local/state')}), \
                 patch.object(module, 'agent_working', side_effect=[True, False]), \
                 patch.object(module, 'power_state', return_value=(False, 50)), \
                 patch.object(module, 'command', side_effect=toggle), \
                 patch.object(module.signal, 'signal'), \
                 patch.object(module.time, 'sleep', side_effect=[None, KeyboardInterrupt]), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    module.agents_inhibitor()
            self.assertEqual(calls, [('omarchy-toggle-idle', 'stay-awake'),
                                     ('omarchy-toggle-idle', 'allow-idle')])
            self.assertFalse(awake.exists())


if __name__ == '__main__':
    unittest.main()
