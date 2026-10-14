#!/bin/bash
# Narrow Dell firmware operation; called only after an explicit setup opt-in.
set -euo pipefail
action=${1:-status}
case $action in
  status|disable|restore) ;;
  *) echo 'Usage: adapter-warning.sh [status|disable|restore]' >&2; exit 2 ;;
esac
[[ $(cat /sys/class/dmi/id/product_name) == 'Latitude 7350 Detachable' ]] || {
  echo 'This firmware setting is only managed on the Dell Latitude 7350 Detachable.' >&2; exit 1;
}
attribute=/sys/class/firmware-attributes/dell-wmi-sysman/attributes/PowerWarn/current_value
[[ -f $attribute ]] || { echo 'This BIOS does not expose the adapter-warning setting.' >&2; exit 1; }
previous=$(sudo cat "$attribute")
case $previous in Enabled|Disabled) ;; *) echo "Unexpected firmware value: $previous" >&2; exit 1 ;; esac
backup=${XDG_STATE_HOME:-$HOME/.local/state}/dell-power/adapter-warning.previous
case $action in
  status) printf 'Adapter warnings: %s\n' "$previous"; exit ;;
  disable)
    target=Disabled
    if [[ $previous == Disabled ]]; then
      echo 'Adapter warnings are already disabled.'
      exit
    fi
    mkdir -p -- "${backup%/*}"
    if [[ ! -e $backup ]]; then
      (umask 077; printf '%s\n' "$previous" >"$backup")
    fi
    ;;
  restore)
    [[ -f $backup ]] || { echo 'No saved pre-install firmware value to restore.' >&2; exit 1; }
    target=$(cat "$backup")
    case $target in Enabled|Disabled) ;; *) echo 'Invalid saved firmware value.' >&2; exit 1 ;; esac
    ;;
esac
printf '%s\n' "$target" | sudo tee "$attribute" >/dev/null
actual=$(sudo cat "$attribute")
[[ $actual == "$target" ]] || { echo "Firmware verification failed: expected $target, got $actual" >&2; exit 1; }
printf 'Adapter warnings: %s -> %s (verified).\n' "$previous" "$actual"
