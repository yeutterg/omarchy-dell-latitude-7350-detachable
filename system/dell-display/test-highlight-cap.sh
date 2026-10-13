#!/bin/bash
# Temporarily compare stronger caps in normal apps; restore on exit.
set -euo pipefail

original=$(hyprctl -j getoption decoration:screen_shader | jq -er '.str')
directory=$(mktemp -d /tmp/dell-highlight-test.XXXXXX)

set_shader() {
  local expression
  expression=$(DELL_SHADER_PATH="$1" lua -e 'io.write(string.format("hl.config({decoration={screen_shader=%q}})", os.getenv("DELL_SHADER_PATH")))')
  hyprctl eval "$expression" >/dev/null
}

cleanup() {
  if set_shader "$original"; then
    rm -rf -- "$directory"
    printf '\nRestored the original highlight shader.\n'
  else
    printf '\nCould not restore the shader. Run hyprctl reload before deleting %s.\n' "$directory" >&2
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Keep the same artifact visible in your app. Switch back here to advance.\n'
printf 'Each cap remains active until you press Enter. Ctrl+C restores and exits.\n'
for level in 240 224 200 160 128; do
  shader="$directory/cap-$level.frag"
  cat >"$shader" <<GLSL
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;
void main() {
    vec4 pixel = texture(tex, v_texcoord);
    fragColor = vec4(min(pixel.rgb, vec3($level.0 / 255.0)), pixel.a);
}
GLSL
  set_shader "$shader"
  errors=$(hyprctl configerrors)
  if [[ -n ${errors//[[:space:]]/} ]]; then
    printf 'Configuration error: %s\n' "$errors" >&2
    exit 1
  fi
  printf '\nCap %s/255 active. Inspect the SAME area; note whether the artifact remains.\n' "$level"
  read -r -p 'Press Enter for the next cap (or restore after 128): ' _
done
