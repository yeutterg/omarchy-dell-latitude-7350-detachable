# omarchy-latitude-7350-detachable

[Omarchy](https://omarchy.org) fixes and tweaks for the **Dell Latitude 7350
Detachable**: working audio, sane side volume buttons, and no window
transparency artifacts.

Generic tablet behaviour (on-screen keyboard, Stay Awake with the cover closed)
lives in `omarchy-tablet`. Install that too; this repo loads after it.

## What's included

| Change | What it does |
|---|---|
| Audio: camera monitor off | Stops WirePlumber stalling on the IPU6 camera nodes, which left the machine with no sound. Cameras aren't exposed through PipeWire. |
| Audio: internal mic off | Keeps the built-in mic closed so a failed wake after suspend can't jam the sound card. The headset-jack mic still works. |
| Volume buttons | One step per tap, repeat only when held. The side buttons report their release late, so one tap used to jump several steps. |
| No transparency | All windows fully opaque; Omarchy's slight transparency showed as light-leak artifacts in Chromium on this panel. |

Details, reasons, trade-offs and when each fix can be removed are in
[CHANGES.md](CHANGES.md), along with known hardware issues.

## Requirements

- Omarchy (Hyprland, Lua config) on a Dell Latitude 7350 Detachable
- Recommended: `omarchy-tablet`

## Install

```bash
git clone https://github.com/<you>/omarchy-latitude-7350-detachable ~/dotfiles/omarchy-latitude-7350-detachable
~/dotfiles/omarchy-latitude-7350-detachable/install.sh
hyprctl reload
systemctl --user restart wireplumber
```

`install.sh` refuses to run on other hardware unless given `--force`. It
symlinks everything under `home/` into `$HOME`, so editing a file in `~/.config`
edits the repo. A real file already in the way is moved aside to
`<file>.pre-dotfiles`. It also adds one line to `~/.config/hypr/hyprland.lua`
that loads `~/.config/hypr/extras/*.lua` in name order. This repo's Hyprland
settings are `extras/60-latitude-7350-detachable.lua`, after `omarchy-tablet`'s
`50-tablet.lua`.

To uninstall, delete the symlinks that point into this repo, and rename any
`*.pre-dotfiles` files back.

## Layout

```
home/                 mirrored into $HOME as symlinks
  .config/hypr/extras/60-latitude-7350-detachable.lua   Hyprland: volume keys, opacity
  .config/wireplumber/wireplumber.conf.d/                audio fixes
install.sh            creates the links
CHANGES.md            every change from Omarchy's defaults, with reasons
```
