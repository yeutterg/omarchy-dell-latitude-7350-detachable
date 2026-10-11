#!/bin/bash

# Link this repo's home/ tree into $HOME (home/.config/x -> ~/.config/x).
# Safe to re-run. A real file already at a target is moved aside to
# <file>.pre-dotfiles before being replaced by a link. Pass --force to install
# on hardware this repo doesn't recognise.

set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
force=${1:-}

# Only for the Dell Latitude 7350 Detachable.
product=$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)
if [[ $product != "Latitude 7350 Detachable" && $force != --force ]]; then
  echo "This is a ${product:-unknown machine}, not a Latitude 7350 Detachable. Rerun with --force to install anyway."
  exit 1
fi

link_tree() {
  local rel target
  while IFS= read -r -d '' rel; do
    rel=${rel#./}
    target=$HOME/$rel
    mkdir -p "$(dirname "$target")"

    if [[ -e $target && ! -L $target ]]; then
      mv "$target" "$target.pre-dotfiles"
      echo "Moved existing $target to $target.pre-dotfiles"
    fi

    ln -sfn "$repo/home/$rel" "$target"
    echo "Linked $target"
  done < <(cd "$repo/home" && find . -type f -print0)
}

# Remove links into this repo whose file was moved or deleted here.
prune_stale_links() {
  local link
  while IFS= read -r -d '' link; do
    if [[ $(readlink "$link") == "$repo/"* && ! -e $link ]]; then
      rm "$link"
      echo "Removed stale link $link"
    fi
  done < <(find "$HOME/.config" "$HOME/.local" "$HOME/.claude" -type l -print0 2>/dev/null)
}

# Enable the systemd user units this repo ships (those with an [Install] section).
enable_units() {
  local unit
  [[ -d $repo/home/.config/systemd/user ]] || return 0
  systemctl --user daemon-reload
  for unit in "$repo"/home/.config/systemd/user/*.{service,path,timer}; do
    [[ -f $unit ]] && grep -q '^\[Install\]' "$unit" || continue
    systemctl --user enable --now "${unit##*/}" && echo "Enabled ${unit##*/}"
  done
}

# Install packages from packages.txt that aren't installed yet (asks for sudo).
install_packages() {
  local missing
  [[ -f $repo/packages.txt ]] || return 0
  missing=$(grep -vE '^\s*(#|$)' "$repo/packages.txt" | while read -r pkg; do pacman -Q "$pkg" &>/dev/null || echo "$pkg"; done)
  [[ -n $missing ]] || return 0
  echo "Installing $(echo $missing)"
  sudo pacman -S --needed --noconfirm $missing
}

# Let Ollama use the integrated GPU (a systemd drop-in for its system service),
# and restart it if it's running so it picks up the Vulkan backend.
configure_ollama() {
  local src=$repo/system/ollama-igpu.conf
  local dst=/etc/systemd/system/ollama.service.d/igpu.conf
  pacman -Q ollama &>/dev/null || return 0
  cmp -s "$src" "$dst" && return 0
  sudo install -Dm644 "$src" "$dst"
  sudo systemctl daemon-reload
  sudo systemctl try-restart ollama
  echo "Installed $dst"
}

# EasyEffects: the "Laptop Speakers" preset on the built-in speakers only. The
# preset is RaduTek's "Surface Laptop 3" (no license file upstream, so it's
# downloaded at a pinned commit rather than copied here). Every other output
# falls back to an empty "Off" preset.
configure_easyeffects() {
  local data=$HOME/.local/share/easyeffects rc=$HOME/.config/easyeffects/db/easyeffectsrc
  local preset="$data/output/Laptop Speakers.json"
  local sink=alsa_output.pci-0000_00_1f.3-platform-sof_sdw.HiFi__Speaker__sink
  local url=https://raw.githubusercontent.com/RaduTek/EasyEffects-Presets/4e31be581c4f6b94d1854acb461d9bc524d25805/Surface%20Laptop%203.json
  pacman -Q easyeffects &>/dev/null || return 0
  mkdir -p "$data/output" "$data/autoload/output" "${rc%/*}"
  if [[ ! -f $preset ]]; then
    # +6 dB into the limiter: the preset's compressor cuts 8 dB and nothing
    # restores it, so it played much quieter than without EasyEffects.
    curl -fsSL "$url" | jq '.output["limiter#0"]["input-gain"] = 6.0' >"$preset.tmp" &&
      mv "$preset.tmp" "$preset" && echo "Installed $preset"
  fi
  [[ -f $data/output/Off.json ]] || echo '{"output":{"blocklist":[],"plugins_order":[]}}' >"$data/output/Off.json"
  printf '{\n    "device": "%s",\n    "device-description": "Meteor Lake-P HD Audio Controller Speaker",\n    "device-profile": "Speaker",\n    "preset-name": "Laptop Speakers"\n}\n' \
    "$sink" >"$data/autoload/output/$sink:Speaker.json"
  grep -q '^outputAutoloadingUsesFallback=' "$rc" 2>/dev/null ||
    printf '\n[Window]\noutputAutoloadingUsesFallback=true\noutputAutoloadingFallbackPreset=Off\n' >>"$rc"
}

# Hyprland only loads ~/.config/hypr/extras/*.lua once hyprland.lua asks for it.
# Add that one line (after Omarchy's toggles, or at the end) if it's missing.
ensure_hypr_extras_loader() {
  local conf=$HOME/.config/hypr/hyprland.lua
  local loader
  loader=$(cat <<'LUA'
for file in io.popen("find -L ~/.config/hypr/extras -maxdepth 1 -type f -name '*.lua' 2>/dev/null | sort"):lines() do dofile(file) end
LUA
)
  [[ -d $repo/home/.config/hypr/extras && -f $conf ]] || return 0
  grep -qF "$loader" "$conf" && return 0

  local block="
-- Drop-in files from repos like omarchy-tablet, loaded in name order.
$loader"
  if grep -q '^require("default.hypr.toggles")' "$conf"; then
    BLOCK=$block awk '{ print } /^require\("default\.hypr\.toggles"\)/ { print ENVIRON["BLOCK"] }' "$conf" >"$conf.tmp"
    mv "$conf.tmp" "$conf"
  else
    printf '%s\n' "$block" >>"$conf"
  fi
  echo "Added the hypr/extras loader to $conf"
}

link_tree
prune_stale_links
configure_easyeffects
enable_units
install_packages
configure_ollama
ensure_hypr_extras_loader

echo "Done. Run 'hyprctl reload' to apply Hyprland changes; some changes (environment.d, WirePlumber, input method) apply on next login."
