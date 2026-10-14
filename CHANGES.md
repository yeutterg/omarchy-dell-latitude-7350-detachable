# Changes from Omarchy's defaults

Every intentional deviation from what Omarchy ships, for the Dell Latitude 7350
Detachable only. Git history has the exact diffs.

### On-screen keyboard: detect the keyboard dock by its touchpad — 2026-10-12
- **File:** `home/.config/omarchy/onscreen-keyboard.json` —
  `{"detachableDevice": "1066 0041 Detachable"}` for the
  io.github.yeutterg.onscreen-keyboard plugin.
- **Why:** intel-hid only creates "Intel HID switches" on the switch's first
  change after boot, so the keyboard plugin couldn't tell it was detached and
  never popped up. The dock's Cirque devices ("Cirque Cirque Kenai 1066 0041
  Detachable Mouse/Touchpad") exist only while attached.
- **Watch:** if the dock's devices are renamed by a kernel update, the keyboard
  falls back to the switch alone.

### Hide disconnected microphone jacks — 2026-10-12
- **Files:** Audio panel `Panel.qml` and `dell-audio-source-availability`.
- **Change:** Hide inputs whose ports are explicitly unavailable, including the
  unplugged Headset Microphone. Built-in Microphone and virtual inputs remain
  visible when availability is unknown. Refresh every five seconds while the
  panel is open, including on opening; filter cached and default entries too.
- **Validation:** QML parsing passed. Live jack state reports the headset absent
  and built-in microphone available; simulated connected/disconnected ports
  confirm the helper handles both states. Plugin reloaded successfully.

### Built-in microphone restored and input labels clarified — 2026-10-12
- **Files:** `system/dell-internal-mic/`, `install.sh`, audio plugin `Model.js`.
  Removed the old WirePlumber microphone-disable rule.
- **Change:** DKMS replacement `dell-internal-mic/7.2.8`, containing the unmodified
  RT712/RT1713 microphone source and headers from Linux stable v7.2.8. Includes
  upstream stream-type initialization fix 03a5699a0a04. It uses stable upstream
  cache-resume behavior rather than Omarchy 7.2.5's stricter backported behavior,
  which failed with -61/-22 and could remove the HiFi profile.
  The default recording device is now the physical built-in microphone.
  Input labels distinguish Built-in Microphone, Headset Microphone, and
  Microphone Effects (virtual). Technical node names are unchanged.
- **Validation:** Successful direct ALSA recording, then nonzero stereo PipeWire
  recordings with the stable module, normal format negotiation, WirePlumber
  restart, and a 15-second suspend/resume. No new audio-driver errors after resume.
  Speaker profile remained available; original speaker volume/mute restored.
  Full speech quality and longer-term resume reliability need ordinary use.
- **Trials removed:** Keeping the codec awake broke UCM mute writes; keeping its
  SoundWire link awake did not fix the stock driver. A forced 32-bit format alone
  still recorded silence. No trial power rule or format override is retained.
  One failed stock-driver reprobe crashed WirePlumber in libspa-alsa; controller
  rebind restored the stack. The stock kernel itself remains installed.

### Clear audio output choices — 2026-10-12
- **Files:** `home/.config/omarchy/plugins/greg.audio/` (cloned stock audio panel).
- **Change:** Label the Dell speaker output "Built-in Speakers" and its headphone
  jack "3.5 mm Headphones". Hide `easyeffects_sink` from the output picker:
  it is an internal processing endpoint, needed for EasyEffects speaker EQ.
  Resolve the selected output through the existing physical-volume sink so
  the hardware row remains selected when processing is the default.
  PipeWire node names and EasyEffects autoload rules are unchanged.
- **Activation:** The live shell configuration selects `greg.audio` instead of
  `omarchy.audio`. On another installation, replace that widget ID in
  `~/.config/omarchy/shell.json` after running `install.sh`.
- **Validation:** QML parsing and model label checks. No audio routing, volume,
  mute state, or effects preset changes.

### Detachable touchpad scroll acceleration — 2026-10-12
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`.
- **Change:** A device-specific custom libinput profile for the Cirque touchpad.
  Natural two-finger scrolling retains the 0.4 base multiplier; slow gestures
  use a 0.8x curve multiplier. Following user feedback, the initial slow curve
  was reduced by about 20%, ordinary fast swipes were boosted, and a further
  high-speed ramp was added: 3.5x at 1.2 units/ms and 5x at 1.4 units/ms
  and above. The existing curve through 1.0 units/ms is unchanged.
  Hyprland requires
  a custom pointer profile to enable scroll acceleration, so a gentle cursor
  curve is supplied too. Other pointer devices retain their existing settings.
  Momentum after finger release remains application-dependent.
- **Validation:** Hyprland reload and configuration error check; subjective
  scrolling and cursor feel still require user feedback.

### Lower hardware brightness minimum — 2026-10-10
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`.
- **Change:** Regular brightness buttons move one hardware level at a time
  below 1% (0.81%, 0.60%, 0.40%, 0.20%). Shift + brightness down goes
  directly to level 1. `home/.local/bin/dell-brightness` shows the measured
  percentage and uses raw brightness/max values for the OSD progress bar.
  External displays use the stock command. `home/.local/bin/dell-brightness-watch`
  (`dell-brightness-watch.service`) watches the backlight with inotify and runs
  `dell-brightness sync` on every write, so the image dimming is undone when
  anything else (Omarchy's display panel slider) raises brightness.
  **2026-10-12:** The `greg.monitor` copy of the display panel (fractional
  readouts, plus a rotation row) and `dell-monitor-state` were removed; the
  panel is Omarchy's own, or omarchy-tablet's display-rotation plugin, both
  1–100%. The watcher replaced what the panel copy did for the dimming.
  Hardware-only changes were hard to distinguish visually. Below 1%,
  hyprsunset additionally scales the image to 80/60/40/20% for raw levels
  4/3/2/1; it returns to 100% at raw level 5. A user comparison confirmed
  software dimming is visibly darker. Readouts remain backlight percentages.
- **Why:** The Intel backlight exposes 496 levels, while Omarchy's normal
  brightness-down binding stops at 1%, rounded to level 5.
- **Validation:** Stepped through all four sub-1% levels in both directions;
  the monitor state reported 0.20 at minimum, and Hyprland reload had no errors.
  Verified gamma follows 80/60/40/20% down and restores to 100% on the way up.
  **2026-10-10 reboot fix:** Close the brightness lock descriptor when starting
  hyprsunset. Otherwise that long-lived child holds the lock after autostart
  and all later button presses are silently dropped. Reproduced by finding
  hyprsunset holding `/run/user/1000/dell-brightness.lock`; verified the fixed
  startup and compositor-launched up/down commands release it.

### Speaker EQ with EasyEffects — 2026-10-11
- **Files:** `packages.txt` (`easyeffects`, `calf`, `lsp-plugins-lv2`),
  `home/.config/systemd/user/easyeffects.service`,
  `home/.local/share/easyeffects/output/{Laptop Speakers,Off}.json`,
  `home/.local/share/easyeffects/autoload/output/…HiFi__Speaker__sink:Speaker.json`,
  `install.sh` (`configure_easyeffects`: fallback preset `Off`).
- **Change:** EasyEffects (`--service-mode`) applies "Laptop Speakers" to the
  built-in speakers: calf bass enhancer (amount 13, harmonics 6.5, scope
  200 Hz) → EQ (+1.5/+2/+1.5 dB at 120/160/200 Hz) → 85 Hz high-pass (x3) →
  limiter (+4 dB in). Every other output falls back to "Off". Omarchy ships no
  audio effects.
- **Why:** The speakers (RT1318 amp) play uncorrected on Linux; Windows applies
  Dell's Waves MaxxAudio tuning, which has no Linux equivalent. Tuned by ear.
- **History:** Started from RaduTek's "Surface Laptop 3" preset. It loaded with
  its high-pass as an 85 Hz *low*-pass (the EasyEffects 7 format has no filter
  `type`, so 8.x defaults to Low-pass), and its 0.8–2 kHz cuts and compressor
  made it quiet and muffled. Replaced with this smaller chain. More bass
  (amount 16, +3/+4/+3 dB, +6 dB limiter) distorted.
- **Cost:** ~80 MB of packages; a little CPU while audio plays.
- **Watch:** The autoload file name depends on the sink name and route
  description; if PipeWire renames them, the preset stops auto-applying.
  After a resume the speaker amp once stayed silent until PipeWire restarted.
### Built-in display at 2x — 2026-10-05
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`
- **Change:** `hl.monitor` for `eDP-1` with `scale = 2` (Omarchy default:
  `"auto"` for every monitor). Previously set by editing `~/.config/hypr/monitors.lua`,
  which is back to Omarchy's template.
- **Why:** Set by hand before this repo existed; an integer scale suits the
  2880x1920 panel. Only the built-in panel is affected.

### Ollama on the integrated GPU — 2026-10-05
- **Files:** `packages.txt`, `system/ollama-igpu.conf` (installed to
  `/etc/systemd/system/ollama.service.d/igpu.conf`), `install.sh`.
- **Change:** Installs `ollama-vulkan` and sets `OLLAMA_IGPU_ENABLE=1` for
  `ollama.service`. `install.sh` now installs missing packages instead of only
  listing them. Omarchy ships no Ollama.
- **Why:** The Intel Meteor Lake graphics have no CUDA or ROCm; Vulkan through
  Mesa is the backend that runs on them. Ollama skips integrated GPUs unless
  told otherwise. Kept here because the right backend depends on the GPU.
- **Cost:** ~55 MB. `install.sh` asks for sudo.
- **Watch:** `journalctl -u ollama` should list a Vulkan device at startup.

### Disable WirePlumber's V4L2 camera monitor — 2026-10-04
- **File:** `home/.config/wireplumber/wireplumber.conf.d/disable-v4l2-monitor.conf`
- **Change:** `wireplumber.profiles.main.monitor.v4l2 = disabled`.
- **Why:** With `intel-ipu7-camera` 1.0.6 (installed by Omarchy's hardware
  setup), WirePlumber 0.5.17 stalls its event queue on the ~48 raw IPU6 camera
  nodes. Everything queued after that waits forever: the sound card stays on the
  `off` profile, no default output is chosen, and streams never link, so there
  is no sound. Confirmed by toggling this setting.
- **Cost:** Cameras are not exposed as PipeWire nodes. Apps that open
  `/dev/video*` directly are unaffected.
- **Remove when:** WirePlumber or `intel-ipu7-camera` fixes the stall.

### Volume keys: one step per tap, hold to repeat — 2026-10-05
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`
- **Change:** Replaces Omarchy's `XF86AudioRaiseVolume`/`XF86AudioLowerVolume`
  bindings (Hyprland key repeat, `repeating = true`). A press steps the volume
  once (5%); after a 600 ms hold it repeats every 100 ms until release. Done with
  press/release bindings and `hl.timer` in Lua. Alt + volume keys (1% steps) are
  unchanged.
- **Why:** The tablet's side volume buttons (`intel-hid-events`) report their
  release ~470 ms after a tap. With Omarchy's 250 ms repeat delay, one tap
  jumped the volume several steps (measured: 30% → 60%). Hyprland can't set
  repeat timing per device (`hl.device` ignores `repeat_delay`), and running
  separate press/release commands raced on the keyboard keys, so the hold
  logic lives in Hyprland's Lua.
- **Watch:** If Omarchy changes its volume bindings or
  `omarchy-audio-output-volume`, update these.

### Disable the internal mic (DMIC) — 2026-10-05
- **Superseded 2026-10-12:** Removed after the stable upstream driver replacement
  passed real recording and suspend/resume checks; see above.
- **File:** `home/.config/wireplumber/wireplumber.conf.d/disable-internal-mic.conf`
- **Change:** `node.disabled = true` for the `sof-soundwire` node on ALSA
  PCM 4 (the rt713 DMIC, "Microphone").
- **Why:** After a suspend/resume the DMIC codec can fail to wake
  (`rt712-sdca-dmic … ASoC error (-61)`). Opening it then jams the card: the
  `HiFi` profile disappears and there is no speaker or headphone output until a
  reboot. `intel-ipu7-camera`'s `v4l2-relayd@ipu7` drop-in restarts WirePlumber
  on every resume, which re-opens the mic. Seen 2026-10-04 and 2026-10-05
  (08:50 resume, 08:50:21 mic error, card stuck on `off`).
- **Cost:** No internal mic. The headset-jack mic (PCM 1) still works.
- **Status:** Not yet confirmed across a suspend/resume.
- **Remove when:** A kernel update fixes the DMIC resume.

### Speaker audio recovery — 2026-10-11
- **Observed:** Audio was silent after keyboard detachment. The card remained
  present with no new codec errors, but used the Pro Audio profile with the
  empty headphone-jack output selected and the hardware speaker switch off.
- **Recovery:** Restored the `HiFi` profile, selected its Speaker sink, and
  cleared mute. WirePlumber saved the profile and default speaker selection.
- **Validation:** Playback completed without driver errors; the user confirmed
  hearing the test tone. Keyboard detachment as the cause is not established.

## Known issues (not config changes)

- **Infrared camera investigation** — 2026-10-10. Firmware exposes
  `OVTI00AB:00` behind the USBIO I2C bridge, in addition to `OVTI08F4`
  and `OVTI8856`. The packaged kernel originally had no ACPI match for this
  sensor. The experimental driver now binds it, and libcamera streams
  640x480 monochrome R10 images. A face-positioned capture confirms the front
  camera. The IR emitter still needs verification.
  The [upstream ACPI discussion](https://lists.openwall.net/linux-kernel/2026/07/28/1593)
  identifies OVTI00AB as OG0VA1B and describes experimental IPU6 integration.
  Subsequently installed the experimental OG0VA1B sensor and patched IPU
  bridge via `dell-ir-camera/0.1` DKMS and rebuilt the Limine UKI.
  Reboot resolved the initial deferred graph endpoint. Found and corrected a
  gain-register mismatch in the imported driver: OG0VA1B needs `0x3508` with
  a four-bit shift, rather than the OG0VE1B layout. Version 0.2 is installed and
  live-loaded. Automatic exposure now converges to its target in two steps
  (4129 lines, gain 128); active illumination remains unverified. Continuous automatic
  exposure is tested and the root-owned recognition runtime is installed.
  A PIN-preserving face lock plugin is prepared. Recognition enrollment and PAM/lock activation remain
  incomplete. Source and rollback details are in `system/dell-ir-camera/`
  and `system/dell-face-auth/`. No PAM changes have been made.

- **Internal mic (RT1713, SoundWire link 3) can lock up** — 2026-10-04. Opening
  the internal mic failed in the kernel (`rt712-sdca-dmic … ASoC error (-61)`),
  then the codec stopped responding (`SCP Msg trf timed out`). While it is stuck,
  the UCM `HiFi` profile cannot initialise and there is no audio output at all.
  A reboot resets it. Recurred after a resume on 2026-10-05. The 2026-10-12
  stable-driver replacement restored recording and passed a suspend/resume test.

- **Chromium display artifacts** — 2026-10-05. Light-leak / faded-polarizer-like
  artifacts in Chromium. Not caused by window transparency: they remained with
  every window forced opaque, so that override was removed.
  Investigation on 2026-10-12 reproduced the effect above white squares in a
  native fullscreen image viewer, including with PSR2 disabled and full-screen
  damage redraws enabled. A gray square and uniform dark-gray field were clean.
  Screenshot pixels were exactly the expected flat colors with sharp edges;
  the physical-screen effect did not appear in the capture. Forcing Chromium
  and Foot opaque, including ignoring surface alpha, did not fix it. Changing
  output from XRGB8888 to XRGB2101010 changed the artifact from yellow/red to
  green, but did not remove it. No display-link errors or GPU resets were found.
  Baseline scanout used Intel MTL RC_CCS_CC compressed tiled buffers (modifier
  0x010000000000000f). A temporary UWSM environment drop-in disables DRM/EGL
  modifiers for the next desktop session to test that path. This is a pending
  diagnostic, not a confirmed fix. After reboot at 16:44 on 2026-10-12, the
  compositor log confirmed XR24 scanout buffers with modifier 0x0 (LINEAR).
  The user confirmed the artifact remained after that reboot, ruling out this
  workaround. The environment overrides were removed; the existing managed
  drop-in is now inert. Log out and back in to restore default allocation.
  The issue remains unresolved. Repeat the browser-independent test
  using `bash system/dell-display/test-contrast.sh` (Right/Left changes patterns,
  Esc closes; it does not modify any settings). Add `--white-levels` to compare
  rectangle levels 255, 250, 240, 224, 200, 160, and 128 on the same dark field.
  Pixel-format, full-redraw, and opaque-surface trials were reverted.
  The white-level test showed artifacts only at 255; 250 and all lower test
  levels initially appeared clean. A final-output highlight cap at 250/255
  seemed to help normal apps, but neither 240 nor a follow-up sweep through
  240, 224, 200, 160, and 128 removed the artifact. The user confirmed the
  configured shader path and no config errors before the sweep. Removing the
  cap and reloading made the artifact much worse, so the 240/255 shader and
  software-cursor override were restored as a confirmed partial mitigation.
  The effect remains visible: this is not a complete fix and its underlying
  cause is still unknown. The temporary sweep script remains as a diagnostic,
  with automatic restoration of the prior shader.
  The remaining effect has not been identified. An independent OS comparison
  with the same white-on-dark pattern would distinguish the Linux display path
  from a panel-side effect more effectively than more compositor tweaks.

# Power and startup — 2026-10-13

- EasyEffects now starts with `--service-mode --hide-window`, preserving the
  speaker preset without opening its window at login.
- Prior-boot logs showed repeated locking but no suspend until UPower's
  critical-battery request at 20:54:22; the journal ends at s2idle entry. The
  persisted power profile was performance. Omarchy's idle plugin had no sleep
  action. No completed hibernation or precise historical drain rate was found.
- Added the Dell power manager, timed sleep/hibernate drop-ins, a 7% direct
  hibernation critical-battery policy, and a cover-inhibitor override that
  excludes EasyEffects' processing streams. See `system/dell-power/README.md`
  for behavior, installation, diagnostics, and rollback.
- Policy tests cover battery/AC timing, activity/inhibitor resets, low-battery
  disk sleep, retry spacing, and real audio versus processing streams. Runtime
  installation and physical suspend/hibernate round trips are pending: this
  agent session cannot access the service buses or write system configuration.
- Corrected the installer resume-device preflight: Btrfs `findmnt MAJ:MIN`
  reports the virtual filesystem device, not the backing block device. It now
  resolves the swap filesystem source without its subvolume suffix and compares
  the block device's actual major/minor numbers with `/sys/power/resume`.
- User completed installation; the service log confirmed AC balanced, and the
  sleep/logind/UPower configuration matched the intended policy. Physical sleep
  round trips remain pending.
- Separated reusable tablet policy into `.local/lib/tablet-power/manager.py`.
  The Dell entry point and hardware-specific installer stay in this repo.
  Added an override for the tablet agent watcher: five-second local checks,
  no completion grace, automatic ownership cleanup, and manual-toggle respect.
  Reduced unnecessary audio/inhibitor polling during active use or Stay Awake.
- Documented the optional Dell `PowerWarn` firmware setting for suppressing
  the below-45 W adapter warning. No BIOS setting was changed automatically.
- Updated the tablet low-battery hook to hibernate a closed, undocked tablet
  directly after releasing Stay Awake, instead of leaving it in plain suspend.
