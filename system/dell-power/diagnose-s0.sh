#!/bin/bash
# Read-only hardware diagnostics after a sustained suspend/resume test.
set -euo pipefail
report=$(mktemp /tmp/dell-s0.XXXXXX)
sudo bash <<'REPORT' >"$report"
set -u
printf 'Kernel: '; uname -r
printf 'Sleep modes: '; cat /sys/power/mem_sleep
printf 'Last wake IRQ: '; cat /sys/power/pm_wakeup_irq
for name in slp_s0_residency_usec substate_residencies substate_requirements \
            substate_status_registers lpm_status lpm_live_status \
            slp_s0_debug_status package_cstate_show ltr_show; do
  file=/sys/kernel/debug/pmc_core/$name
  if [[ -r $file ]]; then
    printf '\n[%s]\n' "$name"
    cat "$file"
  fi
done
printf '\n[Available PMC files]\n'
find /sys/kernel/debug/pmc_core -maxdepth 2 -type f -printf '%P\n' 2>/dev/null
printf '\n[Wake sources]\n'
cat /sys/kernel/debug/wakeup_sources
printf '\n[ACPI wake devices]\n'
cat /proc/acpi/wakeup
printf '\n[Device runtime power]\n'
for device in /sys/bus/pci/devices/* /sys/bus/usb/devices/*; do
  [[ -r $device/power/runtime_status ]] || continue
  printf '%s ' "${device##*/}"
  for name in control runtime_status wakeup; do
    [[ -r $device/power/$name ]] || continue
    printf '%s=%s ' "$name" "$(cat "$device/power/$name")"
  done
  printf '\n'
done
printf '\n[Suspend statistics]\n'
for file in /sys/power/suspend_stats/*; do
  [[ -r $file ]] && printf '%s=%s\n' "${file##*/}" "$(cat "$file")"
done
REPORT
printf 'Saved read-only S0 diagnostics to %s\n' "$report"
printf 'Send this path to the assistant so it can inspect the report.\n'
