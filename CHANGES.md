# Changes from Omarchy's defaults

Every intentional deviation from what Omarchy ships, for the Dell Latitude 7350
Detachable only. Git history has the exact diffs.

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
- **File:** `home/.config/hypr/extras/60-latitude-7350-detachable.lua`
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

### No window transparency — 2026-10-05
- **File:** `home/.config/hypr/extras/60-latitude-7350-detachable.lua`
- **Change:** `o.window(".*", { opacity = "1 1" })`, loaded after Omarchy's
  rules (Omarchy default: `0.985 0.96`; browsers `1.0 0.985`).
- **Why:** Chromium showed light-leak/faded-polarizer-like artifacts that
  appear to come from window transparency on this machine. Transparency isn't
  wanted anyway.

## Known issues (not config changes)

- **Internal mic (RT1713, SoundWire link 3) can lock up** — 2026-10-04. Opening
  the internal mic failed in the kernel (`rt712-sdca-dmic … ASoC error (-61)`),
  then the codec stopped responding (`SCP Msg trf timed out`). While it is stuck,
  the UCM `HiFi` profile cannot initialise and there is no audio output at all.
  A reboot resets it. Recurred after a resume on 2026-10-05; the internal mic is
  now disabled (see "Disable the internal mic" above).
