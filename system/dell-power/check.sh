#!/bin/bash
# Read-only report by default. Sleep tests require an explicit argument.
set -euo pipefail
printf 'Kernel sleep modes: '; cat /sys/power/mem_sleep
printf 'Resume device/offset: '; paste -sd ' ' /sys/power/resume /sys/power/resume_offset
cat /proc/swaps
busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanHibernate
powerprofilesctl get
systemctl --user --no-pager status easyeffects.service dell-power-manager.service || true
omarchy-shell lock status
omarchy-shell idle status
systemd-inhibit --list --no-pager
systemd-analyze cat-config systemd/sleep.conf
journalctl --user -u dell-power-manager.service -n 20 --no-pager
if [[ ${1:-} == --sleep-test ]]; then
  mode=${2:-}
  [[ $mode == suspend || $mode == hibernate ]] || {
    echo 'Usage: check.sh --sleep-test suspend|hibernate' >&2; exit 1;
  }
  boot=$(cat /proc/sys/kernel/random/boot_id)
  since=$(date --iso-8601=seconds)
  capacity=$(cat /sys/class/power_supply/BAT0/capacity)
  status=$(cat /sys/class/power_supply/BAT0/status)
  if (( capacity < 20 )) && [[ $status != Charging && $status != Full ]]; then
    echo 'Connect the charger or charge above 20% before a sleep validation test.' >&2
    exit 1
  fi
  # Read PMC residency when available. Rising residency across suspend proves
  # the platform reached low-power S0; s2idle entry alone does not prove that.
  pmc=/sys/kernel/debug/pmc_core/slp_s0_residency_usec
  if sudo test -r "$pmc"; then
    before=$(sudo cat "$pmc")
  else
    before=''
  fi
  echo "Testing $mode now. Resume with the power button; this terminal should return."
  systemctl "$mode"
  [[ $(cat /proc/sys/kernel/random/boot_id) == "$boot" ]] || {
    echo 'Boot identity changed; session restoration was not confirmed.' >&2; exit 1;
  }
  echo 'The original process returned. Inspect the kernel sleep/resume evidence below:'
  if [[ -n $before ]]; then
    after=$(sudo cat "$pmc")
    echo "Low-power S0 residency (microseconds): $before -> $after"
  fi
  journalctl -b -k --since "$since" --no-pager | rg 'PM:|suspend|hibernation|resume|error|fail' || true
fi
