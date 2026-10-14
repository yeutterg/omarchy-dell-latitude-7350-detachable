#!/usr/bin/python
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
sys.dont_write_bytecode = True

path = Path(__file__).resolve().parents[2] / 'home/.local/bin/dell-power-manager'
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


if __name__ == '__main__':
    unittest.main()
