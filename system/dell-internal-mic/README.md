# Dell RT1713 built-in microphone

Temporary replacement for `snd-soc-rt712-sdca-dmic` on the Latitude 7350
Detachable. The three codec source/header files are unmodified from upstream
Linux stable **v7.2.8**, GPL-2.0-only:
https://github.com/gregkh/linux/tree/v7.2.8/sound/soc/codecs

This includes the upstream fix for uninitialized `stream_config.type`:
https://kernel.googlesource.com/pub/scm/linux/kernel/git/robh/linux/+/03a5699a0a04309c597683967aaaf25d1e555ea2

It also uses stable v7.2.8's cache-resume behavior instead of the stricter
cache-error handling backported into the installed Omarchy 7.2.5 module.
That installed module returned -61, then -22, on microphone runtime wake-up.
WirePlumber could lose the HiFi profile; one reprobe also crashed in
PipeWire's ALSA library. The replacement builds against the current kernel's
headers. No other audio codec or firmware is replaced.

## Install

```sh
sudo install -d /usr/src/dell-internal-mic-7.2.8
sudo cp system/dell-internal-mic/{rt712-sdca-dmic.c,rt712-sdca-dmic.h,rt712-sdca.h,Makefile,dkms.conf,LICENSE} /usr/src/dell-internal-mic-7.2.8/
sudo dkms install dell-internal-mic/7.2.8
sudo limine-mkinitcpio
```

Reboot to load it (or perform a controlled audio-controller unbind/rebind).
The old WirePlumber microphone-disable rule must be removed; `install.sh`
prunes its stale link. Select Built-in Microphone as the recording default.

## Rollback

Reinstall the old WirePlumber disable rule from Git history before reverting
this module, to protect speaker audio on the affected kernel. Then:

```sh
sudo dkms remove dell-internal-mic/7.2.8 --all
sudo limine-mkinitcpio
```

Reboot. Re-evaluate this replacement when updating the kernel; remove it when
the stock driver has been verified with actual microphone recordings after
idle, WirePlumber restart, and suspend/resume. DKMS build success alone is
not an audio functionality test. Experimental recordings remain in `/tmp`,
not in the repository.
