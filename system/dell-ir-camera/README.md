# Experimental Dell infrared camera bring-up

Sources copied from https://github.com/bamarc/dragonfly-folio-camera-mod
commit `8f3cb092de3168b4c4af077fdd506c0bb7ed80c2` (GPL-2.0 SPDX headers retained).
Only the OG0VA1B sensor and IPU bridge modules are used. HP GPIO, flash,
RGB camera and authentication changes are not installed.

The Dell exposes `OVTI00AB:00` on the USBIO I2C bridge at ACPI path
`\_SB_.PC00.LNK0`. Both modules compile against `7.2.5-3-omarchy`.
The live sensor probe defers because the stock IPU bridge does not create
its camera endpoint. A reboot with the patched bridge is required before
sensor capture can be tested. Face authentication is not yet configured.

Installed via DKMS on 2026-10-10, including signed modules and a regenerated
Limine UKI. `libcamera`, `libcamera-ipa`, and `libcamera-tools` are installed.
After reboot, check `readlink /sys/bus/i2c/devices/i2c-OVTI00AB:00/driver`,
`media-ctl -p`, `cam --list`, and kernel logs before attempting streaming.

DKMS install (requires root): copy this directory to
`/usr/src/dell-ir-camera-0.1`, then `dkms add`, `dkms build`, and
`dkms install -m dell-ir-camera -v 0.1`; regenerate initramfs with
`limine-mkinitcpio` on this Omarchy installation (there are no mkinitcpio presets).

Rollback: `dkms remove -m dell-ir-camera -v 0.1 --all`,
`limine-mkinitcpio`, then reboot. This restores the packaged modules.
