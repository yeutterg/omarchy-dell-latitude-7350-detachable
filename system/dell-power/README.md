# Dell tablet power policy

The 2026-10-13 battery incident was primarily an awake-versus-asleep problem:
Omarchy's idle plugin only launched the screensaver and locked the screen. It
never requested suspend. The prior boot repeatedly locked throughout the day,
but the first recorded suspend was UPower's critical-battery
`suspend-then-hibernate` request at 20:54:22. The journal ends at s2idle entry;
there is no completed hibernation or resume. This does not prove a suspend
driver failure: the battery may have exhausted its reserve before hibernation.
The next boot had 4% charge while charging.

The persisted power profile was `performance`. The machine exposes only
`s2idle`, not S3/deep sleep. It already has an approximately 15 GiB disk swap
file, an encrypted root resume device, an RTC ACPI alarm option, and a resume
offset. Hibernation is configured but a successful hardware round trip remains
to be verified. Zram is not hibernation storage. The installer checks the disk
swap's actual Btrfs offset and resume device before enabling this policy.

## Behavior

| Trigger | Action |
| --- | --- |
| Login or charger transition | Power saver on battery; balanced on AC |
| Securely locked, all displays off, no activity/inhibitor | Sleep after 60 seconds on battery or 5 minutes on AC |
| Stay Awake, real playback/recording, or idle/sleep block inhibitor | Defer automatic sleep |
| Input wakes the locked screen | Restart the sleep countdown |
| Cover closes | Suspend then hibernate, unless Stay Awake or real audio inhibits it; retain docked clamshell behavior |
| 30 minutes asleep on battery | Hibernate; stay suspended on AC |
| Locked/off at 10% battery or below | Hibernate directly instead of suspending first |
| 7% battery in active use | UPower hibernates directly, with low/critical warnings at 20%/10% |

Manual power-profile choices persist until the next charger transition.
EasyEffects launches with `--service-mode --hide-window`. Its internal
processing streams do not count as playback in the Dell sleep policy or the
tablet cover inhibitor. Applications remain able to inhibit sleep, and the
existing Omarchy pre-sleep lock service remains responsible for securing the
session. Failed IPC probes defer automatic sleep instead of guessing idle.
No blanket USB/audio/camera autosuspend tweaks are applied.

## Install and verify

Run as your normal desktop user in a terminal:

```bash
bash system/dell-power/install.sh
bash system/dell-power/check.sh
bash system/dell-power/check.sh --sleep-test suspend
bash system/dell-power/check.sh --sleep-test hibernate
```

The installer installs persistent system drop-ins, preserves unrelated UPower
settings, backs up the original UPower file, links the Dell user service, and
starts the policy and hidden EasyEffects. It reloads logind rather than
restarting it. The main repository installer also invokes it.

For each explicit sleep test, resume with the power button. Confirm the same
terminal and applications return, plus keyboard, touchpad, audio, microphone,
Wi-Fi, and charging still work. For hibernation, confirm the kernel journal
shows an image restored and hibernation exit rather than a fresh boot. A
30-minute battery standby test is still needed to verify the RTC-triggered
transition from suspend to hibernate and measure actual drain.

Policy checks: `python system/dell-power/test-policy.py`.

## Rollback

Disable `dell-power-manager.service`, remove the two `60-dell-*.conf` system
drop-ins and the `stay-awake-cover.service.d/60-dell-audio.conf` user override,
restore `/etc/UPower/UPower.conf.pre-dell-power`, then reload logind, restart
UPower, reload the user service manager, and restart `stay-awake-cover.service`.
The existing lock, power-button, and brightness behavior is unchanged.

References: [systemd 261 sleep configuration](https://github.com/systemd/systemd/blob/v261/man/systemd-sleep.conf.xml),
[EasyEffects maintainer's background-start guidance](https://github.com/wwmm/easyeffects/discussions/4866).
