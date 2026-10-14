#!/bin/bash
# Run as the desktop user in a terminal, not as root.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
[[ $(cat /sys/class/dmi/id/product_name) == 'Latitude 7350 Detachable' ]] || {
  echo 'This policy is only for the Dell Latitude 7350 Detachable.' >&2; exit 1;
}
[[ $EUID != 0 ]] || { echo 'Run as the desktop user; sudo is used for system files.' >&2; exit 1; }

busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanHibernate | grep -q '"yes"' || {
  echo 'Hibernation is unavailable. Fix swap/resume before installing this policy.' >&2; exit 1;
}
offset=$(sudo btrfs inspect-internal map-swapfile -r /swap/swapfile)
[[ $offset == "$(cat /sys/power/resume_offset)" ]] || {
  echo 'Swap resume offset is stale. Run omarchy-hibernation-setup and reboot first.' >&2; exit 1;
}
# Btrfs reports a virtual filesystem MAJ:MIN (0:...) through findmnt. Resume
# uses the backing block device instead. --nofsroot strips the subvolume suffix.
swap_source=$(findmnt -nro SOURCE --nofsroot -T /swap/swapfile)
swap_device=$(python - "$swap_source" <<'PY'
import os
import stat
import sys
device = os.stat(sys.argv[1])
if not stat.S_ISBLK(device.st_mode):
    raise SystemExit('Swap filesystem source is not a block device')
print(f'{os.major(device.st_rdev)}:{os.minor(device.st_rdev)}')
PY
)
[[ $swap_device == "$(cat /sys/power/resume)" ]] || {
  echo 'Swap resume device does not match the active root device.' >&2; exit 1;
}
command -v powerprofilesctl >/dev/null

link_file() {
  local relative=$1 target=$HOME/$1
  mkdir -p -- "$(dirname -- "$target")"
  if [[ -e $target && ! -L $target ]]; then
    cp -a -- "$target" "$target.pre-dell-power"
  fi
  ln -sfn -- "$repo/home/$relative" "$target"
}
link_file .local/bin/dell-power-manager
link_file .local/lib/tablet-power/manager.py
link_file .config/systemd/user/dell-power-manager.service
link_file .config/systemd/user/easyeffects.service
link_file .config/omarchy/hooks/battery-low.d/stay-awake-off
if [[ -e $HOME/.config/systemd/user/stay-awake-cover.service ]]; then
  link_file .config/systemd/user/stay-awake-cover.service.d/60-dell-audio.conf
fi
if [[ -e $HOME/.config/systemd/user/stay-awake-agents.service ]]; then
  link_file .config/systemd/user/stay-awake-agents.service.d/60-tablet-power.conf
fi

sudo install -Dm644 "$repo/system/dell-power/60-dell-sleep.conf" /etc/systemd/sleep.conf.d/60-dell-sleep.conf
sudo install -Dm644 "$repo/system/dell-power/60-dell-logind.conf" /etc/systemd/logind.conf.d/60-dell-logind.conf
if ! sudo test -e /etc/UPower/UPower.conf.pre-dell-power; then
  sudo cp -a /etc/UPower/UPower.conf /etc/UPower/UPower.conf.pre-dell-power
fi
# Preserve unrelated UPower settings and comments; update only this policy.
sudo python - "$repo/system/dell-power/UPower.conf" <<'PY'
import configparser
from pathlib import Path
import re
import sys
policy = configparser.ConfigParser()
policy.optionxform = str
policy.read(sys.argv[1])
path = Path('/etc/UPower/UPower.conf')
text = path.read_text()
for key, value in policy['UPower'].items():
    pattern = rf'(?m)^{re.escape(key)}\s*=.*$'
    if re.search(pattern, text):
        text = re.sub(pattern, f'{key}={value}', text)
    else:
        text = text.replace('[UPower]', f'[UPower]\n{key}={value}', 1)
path.write_text(text)
PY
sudo systemctl daemon-reload
sudo systemctl restart upower.service
# logind reloads without ending the session; do not restart logind.
sudo systemctl reload systemd-logind.service
systemctl --user daemon-reload
systemctl --user enable --now easyeffects.service dell-power-manager.service
systemctl --user restart easyeffects.service dell-power-manager.service
if [[ -e $HOME/.config/systemd/user/stay-awake-cover.service ]]; then
  systemctl --user restart stay-awake-cover.service
fi
if [[ -e $HOME/.config/systemd/user/stay-awake-agents.service ]]; then
  systemctl --user restart stay-awake-agents.service
fi
# Explicit opt-in; never change firmware during unattended setup.
attribute=/sys/class/firmware-attributes/dell-wmi-sysman/attributes/PowerWarn/current_value
if [[ -t 0 && -f $attribute ]]; then
  current_warning=$(sudo cat "$attribute")
  if [[ $current_warning == Enabled ]]; then
    printf '\nThe BIOS can pause boot with a low-wattage USB-C charger.\n'
    answer=''
    if read -r -p 'Suppress the Dell low-wattage adapter warning? [y/N] ' answer; then
      case $answer in
        y|Y|yes|YES|Yes) bash "$repo/system/dell-power/adapter-warning.sh" disable ;;
        *) echo 'Adapter warning left unchanged.' ;;
      esac
    else
      echo 'Adapter warning left unchanged.'
    fi
  elif [[ $current_warning == Disabled ]]; then
    echo 'BIOS adapter warnings are already disabled; left unchanged.'
  fi
fi
echo 'Installed. EasyEffects is hidden; the Dell policy is active. Verify hibernate/resume before relying on overnight standby.'
