# Changes from Omarchy's defaults

Every intentional deviation from what Omarchy ships, for the Dell Latitude 7350
Detachable only. Git history has the exact diffs.

### Lower hardware brightness minimum — 2026-10-10
- **File:** `home/.config/hypr/extras/60-dell-latitude-7350-detachable.lua`.
- **Change:** Brightness down takes a final step from raw level 5 (1%) to
  raw level 1; Shift + brightness down goes directly to level 1.
- **Why:** The Intel backlight exposes 496 levels, while Omarchy's normal
  brightness-down binding stops at 1%, rounded to level 5.
- **Validation:** Applied level 1; Hyprland reload succeeded with no config errors.

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

## Known issues (not config changes)

- **Infrared camera investigation** — 2026-10-10. Firmware exposes
  `OVTI00AB:00` behind the USBIO I2C bridge, in addition to `OVTI08F4`
  and `OVTI8856`. No driver is bound to `OVTI00AB`. The installed
  `og0ve1b` module advertises only the OG0VE1B device-tree match,
  with no OG0VA1B/OVTI00AB ACPI support. Only the RGB ov08x40 sensor appears
  in the media topology. This does not establish absence of Windows Hello
  hardware; infrared capture and emitter operation still need verification.
  The [upstream ACPI discussion](https://lists.openwall.net/linux-kernel/2026/07/28/1593)
  identifies OVTI00AB as OG0VA1B and describes experimental IPU6 integration.

- **Internal mic (RT1713, SoundWire link 3) can lock up** — 2026-10-04. Opening
  the internal mic failed in the kernel (`rt712-sdca-dmic … ASoC error (-61)`),
  then the codec stopped responding (`SCP Msg trf timed out`). While it is stuck,
  the UCM `HiFi` profile cannot initialise and there is no audio output at all.
  A reboot resets it. Recurred after a resume on 2026-10-05; the internal mic is
  now disabled (see "Disable the internal mic" above).

- **Chromium display artifacts** — 2026-10-05. Light-leak / faded-polarizer-like
  artifacts in Chromium. Not caused by window transparency: they remained with
  every window forced opaque, so that override was removed.
