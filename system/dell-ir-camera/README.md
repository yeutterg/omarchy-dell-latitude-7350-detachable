# Experimental Dell infrared camera bring-up

Sources copied from https://github.com/bamarc/dragonfly-folio-camera-mod
commit `8f3cb092de3168b4c4af077fdd506c0bb7ed80c2` (GPL-2.0 SPDX headers retained).
Only the OG0VA1B sensor and IPU bridge modules are used. HP GPIO, flash,
RGB camera and authentication changes are not installed.

The Dell exposes `OVTI00AB:00` on the USBIO I2C bridge at ACPI path
`\_SB_.PC00.LNK0`. Both modules compile against `7.2.5-3-omarchy`.
Before reboot, the live sensor probe deferred because the stock IPU bridge
did not create its camera endpoint. The patched bridge resolved this on
reboot. Face authentication is not yet configured.

After reboot on 2026-10-10, the sensor bound successfully, libcamera listed
`\_SB_.PC00.LNK0`, and 640x480 R10 frames streamed (614400 bytes per frame).
Gain 128 and exposure 2000 produce an ambient-light image, but active IR
illumination remains unresolved. Both ACPI TXNW3643 devices report status 0;
there is no Linux torch/strobe LED device for this camera. Do not install the
HP-specific flash or GPIO drivers without establishing the Dell wiring.

Repeatable diagnostic capture: `dell-ir-capture /tmp/ir-preview.pgm` (source
in `home/.local/bin/dell-ir-capture`). This selects the IR camera by its
ACPI ID and finds the sensor subdevice dynamically. Automatic exposure meters
the central region of raw frames, adjusts exposure and gain, and extends frame
length when needed. It favors exposure over gain, caps automatic exposure at
12000 lines (roughly 100 ms), and reports when more light is needed. Exposure,
gain, and frame length are restored on exit. It writes a center-region
percentile-normalized grayscale preview and reports raw intensity levels.
Normalization can amplify sensor noise; inspect face detail, not just preview
brightness. Override gain/exposure for a manual capture using `DELL_IR_GAIN`
/ `DELL_IR_EXPOSURE`. This is an iterative diagnostic, not continuous exposure
control for the future face-authentication capture service.
No flash controls or PAM settings are changed by this diagnostic.

Firmware inspection: IR controller DSC0 maps USBIO pin 1 as handshake and
pin 3 as power enable. Neither is identified as a strobe control. The two
TXNW3643 ACPI devices are disabled, so the HP LM3643 torch setup cannot be
assumed to apply. A face-positioned capture and emitter observation are
required before proceeding to Howdy integration. A face-positioned capture on
2026-10-10 confirmed the front sensor but was substantially underexposed. The
user could not determine whether the emitter lit. A subsequent automatic
exposure test increased from 2000 lines/gain 128 to 12000 lines/gain 511 and
hit its limit below the target intensity; illumination remains unresolved.

Driver correction prepared on 2026-10-10 (DKMS version 0.2): the imported
driver used the OG0VE1B gain register `0x350a` for both sensors. OG0VA1B
analogue gain uses `0x3508`/`0x3509`, with the control value shifted left by
four bits. This is shown in Qualcomm's original OG0VA1B patch:
https://lists.openwall.net/linux-kernel/2026/06/18/772
and independently in Dell's Windows sensor driver. The correction retains
the OG0VE1B register layout for that sensor. Version 0.2 is installed and live-loaded on kernel 7.2.5-3-omarchy.
The corrected driver exposes gain 16..511. An automatic exposure capture
converged in two steps (2000 to 4129 lines at gain 128), reaching central
p80 249 against target 256 without clipping. Active illumination is still
unverified; the image remains noisy in the current lighting.

Windows configuration inspected from Dell's official package C1HHN, A08,
74.22000.2.30, matching system ID 0C64 in `CatalogPC.cab`:
https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=c1hhn
The sensor INF sets IR flash intensity to 50, and the Dell extension sets
`MCUonlyEnabled=1`. These establish a Dell-specific MCU path but do not yet
identify a Linux emitter command. Proprietary driver binaries are retained
only under `/tmp` for inspection, not distributed in this repository.

Installed via DKMS on 2026-10-10, including signed modules and a regenerated
Limine UKI. `libcamera`, `libcamera-ipa`, and `libcamera-tools` are installed.
After reboot, check `readlink /sys/bus/i2c/devices/i2c-OVTI00AB:00/driver`,
`media-ctl -p`, `cam --list`, and kernel logs before attempting streaming.

DKMS install (requires root): copy this directory to
`/usr/src/dell-ir-camera-0.2`, then `dkms add`, `dkms build`, and
`dkms install -m dell-ir-camera -v 0.2`; regenerate initramfs with
`limine-mkinitcpio` on this Omarchy installation (there are no mkinitcpio presets).

Rollback: `dkms remove -m dell-ir-camera -v 0.2 --all` (or `0.1` if that
is still installed),
`limine-mkinitcpio`, then reboot. This restores the packaged modules.

Illumination investigation (2026-10-10): ACPI `INTC10CF` at
`\_SB_.PC00.SPFD.CVFD` is the older SPI CVF/IVSC device, not the
I2C CVS protocol implemented by the installed `intel_cvs` driver. Dell
reference package H28WY maps it to `IVSC.sys` and its parent `INTC10D0`
to `SpiOed.sys`. This detachable's `INTC10D3` USB-SPI ACPI device has
status 0, and its own camera package C1HHN omits those two drivers. Merely
adding `INTC10CF` to the modern CVS match table would not implement its
transport or establish an emitter control. No such match-table change was made.
