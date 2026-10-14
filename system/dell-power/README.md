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
The battery default applies while awake too; workloads do not switch it to
performance. Automatic agent Stay Awake is released on the next five-second
local status check when all agents are idle, waiting for input, exited, or
unavailable. There is no extra 30-second completion grace. Manual Stay Awake
and manually turning it off while a job runs remain respected. The watcher
tracks ownership and releases its own state on clean service shutdown.

The reusable tablet policy lives in
`home/.local/lib/tablet-power/manager.py`; the Dell executable is a thin entry
point. Sleep timing, audio filtering, charger profile transitions, and agent
ownership are generic tablet behavior. Dell-specific hardware gating,
Btrfs resume validation, installation, and firmware instructions stay in
`system/dell-power`. Both are currently versioned in the Dell repo; the generic
module can be transferred to the tablet repo without rewriting its policy.

Polling stays lightweight: the power manager checks every 15 seconds and
only queries lock state while unlocked. It skips inhibitor/audio queries while
Stay Awake is set. Agent checks are every five seconds with a two-second total
local query budget; no network calls or process-tree scanning. The cover
watcher skips audio probes while Stay Awake is set.
EasyEffects launches with `--service-mode --hide-window`. Its internal
processing streams do not count as playback in the Dell sleep policy or the
tablet cover inhibitor. Applications remain able to inhibit sleep, and the
existing Omarchy pre-sleep lock service remains responsible for securing the
session. Failed IPC probes defer automatic sleep instead of guessing idle.
No blanket USB/audio/camera autosuspend tweaks are applied.
The tablet low-battery hook also releases Stay Awake and hibernates a closed,
undocked tablet directly, replacing its old plain-suspend action.

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

Installed on 2026-10-13: the running service journal confirmed `AC: balanced`,
the sleep/logind drop-ins matched, and UPower's direct hibernate action was
installed at 7%. Rerun the installer after updates to reload the services and
install the agent-watcher override. Physical sleep and hibernation verification
is still pending.

## Low-wattage charger warning

Dell documents 27 W as the minimum to operate and charge this model; below
45 W can produce a warning and charge more slowly. A compatible 30 W USB-PD
charger therefore need not block boot just because it is below 45 W. In BIOS
Advanced Setup, disable **Pre-boot Behavior → Adapter Warnings → Enable Dock
Warning Messages**. This controls the adapter warning, not the charger's output.

The same setting is exposed by this machine as
`/sys/class/firmware-attributes/dell-wmi-sysman/attributes/PowerWarn/current_value`,
with supported values `Enabled` and `Disabled`. Interactive setup asks:

```text
Suppress the Dell low-wattage adapter warning? [y/N]
```

Enter `y` to disable it, or press Enter to leave it unchanged. Unattended setup
never changes firmware. If already disabled, setup leaves it alone without
asking again. Only `PowerWarn` is written, with read-back verification. The
previous value is saved under `$XDG_STATE_HOME/dell-power/adapter-warning.previous`
(normally `~/.local/state/dell-power/adapter-warning.previous`). Restore it with:

```bash
bash system/dell-power/adapter-warning.sh restore
```

Leave the broader **Warnings and Errors** setting alone so other errors still
prompt. A 30 W charger will still charge slowly and might not keep up with
heavy workloads. [Dell power requirements](https://www.dell.com/support/manuals/en-us/latitude-13-7350-detachable-laptop/latitude-7350-dtbl-owners-manual/power-requirements-of-latitude-7350-detachable?guid=guid-78f4422e-8d18-4702-a0c9-f917a5499fcf&lang=en-us),
[Dell BIOS options](https://www.dell.com/support/manuals/en-us/latitude-13-7350-detachable-laptop/latitude-7350-dtbl-owners-manual/system-setup-options?guid=guid-160397c4-7aef-4325-82fd-f27722b46f31&lang=en-us).

For each explicit sleep test, wait at least 60 seconds after the screen goes
dark before resuming with the power button. The initial suspend test was woken
almost immediately after preparation and reported zero S0 residency; it does
not establish whether sustained suspend reaches low-power S0. Confirm the same
terminal after resume. A follow-up stayed in s2idle for 77 seconds and resumed
successfully; its actual low-power residency still needs checking. Confirm the
terminal and applications return, plus keyboard, touchpad, audio, microphone,
Wi-Fi, and charging still work. For hibernation, confirm the kernel journal
shows an image restored and hibernation exit rather than a fresh boot. A
30-minute battery standby test is still needed to verify the RTC-triggered
transition from suspend to hibernate and measure actual drain.

Policy checks: `python system/dell-power/test-policy.py`.

## Rollback

Disable `dell-power-manager.service`, remove the two `60-dell-*.conf` system
drop-ins and the `stay-awake-cover.service.d/60-dell-audio.conf` and
`stay-awake-agents.service.d/60-tablet-power.conf` user overrides,
restore `/etc/UPower/UPower.conf.pre-dell-power`, then reload logind, restart
UPower, reload the user service manager, and restart `stay-awake-cover.service`
and `stay-awake-agents.service`. Restore the previous low-battery hook from the
tablet repo (or its `.pre-dell-power` backup if it was a real file).
The existing lock, power-button, and brightness behavior is unchanged.

References: [systemd 261 sleep configuration](https://github.com/systemd/systemd/blob/v261/man/systemd-sleep.conf.xml),
[EasyEffects maintainer's background-start guidance](https://github.com/wwmm/easyeffects/discussions/4866).
