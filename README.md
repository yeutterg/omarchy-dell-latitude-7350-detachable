# Omarchy Dotfiles for Dell 7350 Detachable

[Omarchy](https://omarchy.org) fixes and tweaks for the **Dell Latitude 7350
Detachable**.

**Complementary repo:** generic tablet behaviour (on-screen keyboard, Stay Awake
with the cover closed) is in [omarchy-tablet](https://github.com/yeutterg/omarchy-tablet). Install
that too; this repo loads after it.

## Customizations

| Customization | Summary |
|---|---|
| [Audio fixes](#audio-fixes) | Working sound: WirePlumber's camera monitor and the flaky internal mic are disabled |
| [Volume buttons](#volume-buttons) | One step per tap, repeat only when held |
| [Display scale](#display-scale) | Built-in panel at 2x |
| [Ollama on the GPU](#ollama-on-the-gpu) | Vulkan backend and integrated-GPU support for Ollama |

### Audio fixes
- **Camera monitor off:** WirePlumber stalls on the IPU6 camera's raw nodes,
  leaving the card on the `off` profile with no sound. Cost: cameras aren't
  exposed through PipeWire (apps opening `/dev/video*` directly still work).
- **Internal mic off:** after suspend the DMIC can fail to wake, and opening it
  then jams the card until reboot. The headset-jack mic still works.
- Both can be removed once the kernel/WirePlumber/camera driver bugs are fixed.

### Volume buttons
The side buttons report their release ~470 ms late, so Hyprland's key repeat
turned one tap into several steps. Now a press steps 5% once and only repeats
after a 600 ms hold.

### Display scale
The built-in 2880x1920 panel is set to exactly 2x (1440x960 of space) instead
of Omarchy's `auto`. Other monitors keep Omarchy's setting.

### Ollama on the GPU
- Installs `ollama-vulkan`, Ollama's Vulkan backend, which runs on the Meteor
  Lake integrated graphics through Mesa.
- Ollama ignores integrated GPUs by default, so a systemd drop-in sets
  `OLLAMA_IGPU_ENABLE=1` for `ollama.service`.
- The GPU shares system RAM, so it speeds things up but doesn't allow bigger
  models. Only applies if Ollama is installed.

Full details, measurements and known hardware issues are in
[CHANGES.md](CHANGES.md).

## Install

```bash
git clone https://github.com/yeutterg/omarchy-dell-latitude-7350-detachable ~/dotfiles/omarchy-dell-latitude-7350-detachable
~/dotfiles/omarchy-dell-latitude-7350-detachable/install.sh
hyprctl reload
systemctl --user restart wireplumber
```

`install.sh` refuses to run on other hardware unless given `--force`. It
installs missing packages from `packages.txt` and Ollama's drop-in from
`system/` (asks for sudo), symlinks `home/` into `$HOME` (a real file in the way is moved to
`<file>.pre-dotfiles`) and adds one line to `~/.config/hypr/hyprland.lua` that
loads `~/.config/hypr/extras/*.lua` in name order. This repo's Hyprland settings
are `extras/60-dell-latitude-7350-detachable.lua`. To uninstall, delete the
symlinks into this repo and restore any `*.pre-dotfiles` files.
