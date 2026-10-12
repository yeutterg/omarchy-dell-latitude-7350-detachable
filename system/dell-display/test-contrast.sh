#!/bin/bash
# Reproduce the white-on-dark display artifact without browser rendering or alpha.
set -euo pipefail
directory=$(mktemp -d /tmp/dell-display-contrast.XXXXXX)
trap 'rm -rf -- "$directory"' EXIT

magick -size 2880x1920 xc:'#181818' -fill white \
  -draw 'rectangle 1000,600 1399,999' "$directory/1-white-on-dark.png"
magick -size 2880x1920 xc:'#181818' -fill white \
  -draw 'rectangle 1800,1000 2199,1399' "$directory/2-moved-white.png"
magick -size 2880x1920 xc:'#181818' -fill '#808080' \
  -draw 'rectangle 1000,600 1399,999' "$directory/3-gray-on-dark.png"
magick -size 2880x1920 xc:'#808080' -fill white \
  -draw 'rectangle 1000,600 1399,999' "$directory/4-white-on-gray.png"

echo 'Right/Left: compare patterns. Esc: close. No brightness or display settings are changed.'
imv -f -i dell-contrast-test -w 'Dell contrast diagnostic — Right arrow changes pattern' \
  "$directory/1-white-on-dark.png" "$directory/2-moved-white.png" \
  "$directory/3-gray-on-dark.png" "$directory/4-white-on-gray.png"
