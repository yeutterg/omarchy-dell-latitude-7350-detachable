# Changes from Omarchy's defaults

Every intentional deviation from what Omarchy ships, for the Dell Latitude 7350
Detachable only. Git history has the exact diffs.

### Detachable touchpad scroll acceleration — 2026-10-12
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`.
- **Change:** A device-specific custom libinput profile for the Cirque touchpad.
  Natural two-finger scrolling retains the 0.4 base multiplier; slow gestures
  use a 0.8x curve multiplier and fast swipes approach 1.6x. The initial slow
  curve was reduced by about 20% following user feedback. Hyprland requires
  a custom pointer profile to enable scroll acceleration, so a gentle cursor
  curve is supplied too. Other pointer devices retain their existing settings.
  Momentum after finger release remains application-dependent.
- **Validation:** Hyprland reload and configuration error check; subjective
  scrolling and cursor feel still require user feedback.

### Rotation row in the display panel — 2026-10-12
- **File:** `home/.config/omarchy/plugins/greg.monitor/Panel.qml`.
- **Change:** A ROTATION section after SCALE with three pills (Rotate left,
  Rotate right, Auto) that call omarchy-tablet's `~/.local/bin/tablet-rotate`
  (`turn left|right`, `auto on|off`) and read `tablet-rotate status` on
  refresh. Only Auto shows an on state; left and right are one-off actions. Keyboard navigation works like SCALE (h/l along the row, Enter to
  pick). Hidden when `tablet-rotate` is missing; Auto is dimmed without
  `iio-sensor-proxy`.
- **Why:** The Dell is a detachable, and the stock display panel has no
  rotation.
- **Validation:** Screenshots of the panel showed the row; `tablet-rotate
  inverted` rotated the screen and set touch and pen transform to 2, and
  `normal` restored it. The user confirmed rotation works on the device.
  (First version had 0°/90°/180°/270° pills; replaced with left/right at the
  user's request.)

### Lower hardware brightness minimum — 2026-10-10
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`.
- **Change:** Regular brightness buttons move one hardware level at a time
  below 1% (0.81%, 0.60%, 0.40%, 0.20%). Shift + brightness down goes
  directly to level 1. `home/.local/bin/dell-brightness` shows the measured
  percentage and uses raw brightness/max values for the OSD progress bar.
  The cloned `greg.monitor` panel preserves fractional values and reads them
  through `dell-monitor-state`. External displays use the stock command.
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
  A reboot resets it. Recurred after a resume on 2026-10-05; the internal mic is
  now disabled (see "Disable the internal mic" above).

- **Chromium display artifacts** — 2026-10-05. Light-leak / faded-polarizer-like
  artifacts in Chromium. Not caused by window transparency: they remained with
  every window forced opaque, so that override was removed.
