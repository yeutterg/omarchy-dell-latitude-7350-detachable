-- omarchy-dell-latitude-7350-detachable: Hyprland settings for the Dell Latitude 7350
-- Detachable only. Linked into ~/.config/hypr/extras/ by install.sh; loads after
-- omarchy-tablet's 50-tablet.lua, so it can override it.

-- Progressive acceleration for the detachable touchpad only. A custom profile is
-- required for scroll_points and also replaces libinput's pointer profile.
-- Points are OUTPUT velocities at input intervals of 0.2 units/ms, not gains.
-- Slow scrolling uses 0.8x before the existing 0.4 multiplier. Ordinary swipes
-- keep their previous curve; very fast swipes ramp to 5x at 1.6 units/ms.
-- Above that, the last segment extrapolates linearly with a slope of 5.
hl.device({
  name = "cirque-cirque-kenai-----1066-0041-detachable-touchpad",
  natural_scroll = true,
  scroll_method = "2fg",
  scroll_factor = 0.4,
  accel_profile = "custom 0.2 0.0 0.08 0.20 0.36 0.56 0.72",
  scroll_points = "0.2 0.0 0.16 0.36 0.90 1.44 1.92 4.20 7.00 8.00",
})

-- Side volume buttons report their release ~0.5s late, so Hyprland's key repeat
-- turned a single tap into several steps. Instead: one 5% step on press, and
-- repeat only once held past that late release, until the key is let go. Done in
-- Lua so press and release are handled in order (separate commands raced).
local volume_held = 0 -- bumped on every press and release; a repeat stops once it changes
local hold_delay = 600 -- ms; must exceed the side buttons' ~470ms late release
local repeat_every = 100 -- ms

local function volume_step(action)
  hl.exec_cmd("omarchy-audio-output-volume " .. action)
end

local function volume_press(action)
  return function()
    volume_held = volume_held + 1
    local generation = volume_held
    volume_step(action)

    local function tick()
      if volume_held ~= generation then return end
      volume_step(action)
      hl.timer(tick, { timeout = repeat_every, type = "oneshot" })
    end
    hl.timer(tick, { timeout = hold_delay, type = "oneshot" })
  end
end

local function volume_release()
  volume_held = volume_held + 1
end

hl.unbind("XF86AudioRaiseVolume")
hl.unbind("XF86AudioLowerVolume")
o.bind("XF86AudioRaiseVolume", "Volume up", volume_press("raise"), { locked = true })
o.bind("XF86AudioLowerVolume", "Volume down", volume_press("lower"), { locked = true })
o.bind("XF86AudioRaiseVolume", nil, volume_release, { locked = true, release = true })
o.bind("XF86AudioLowerVolume", nil, volume_release, { locked = true, release = true })

-- Built-in 2880x1920 panel pinned to exactly 2x instead of Omarchy's "auto",
-- so it doesn't depend on Hyprland's guess; an integer scale keeps text crisp.
hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 2 })

-- Panel artifact workaround: full white triggered a physical-screen halo;
-- 250/255 helped but left a faint artifact in normal apps; now test 240/255.
-- Resolve the managed symlink so this works
-- immediately and also when the repository is installed at another location.
local display_config = io.popen('readlink -f -- "$HOME/.config/hypr/extras/60-dell-latitude-7350-detachable.lua"')
local display_config_path = display_config:read("*l")
display_config:close()
assert(display_config_path, "Cannot resolve Dell display configuration")
local shader_path = display_config_path:gsub("/extras/[^/]+$", "/shaders/dell-highlight-cap.frag")
hl.config({
  decoration = { screen_shader = shader_path },
  -- Composite the pointer too, so its white pixels cannot bypass the cap.
  cursor = { no_hardware_cursors = 1 },
})

-- Fractional hardware steps below 1%, with accurate OSD readout.
for _, key in ipairs({ "XF86MonBrightnessDown", "XF86MonBrightnessUp", "SHIFT + XF86MonBrightnessDown" }) do
  hl.unbind(key)
end
o.bind("XF86MonBrightnessDown", "Brightness down", "$HOME/.local/bin/dell-brightness down", { locked = true, repeating = true })
o.bind("XF86MonBrightnessUp", "Brightness up", "$HOME/.local/bin/dell-brightness up", { locked = true, repeating = true })
o.bind("SHIFT + XF86MonBrightnessDown", "Brightness minimum", "$HOME/.local/bin/dell-brightness minimum", { locked = true })
o.exec_on_start("$HOME/.local/bin/dell-brightness --no-osd --monitor eDP-1 sync")
