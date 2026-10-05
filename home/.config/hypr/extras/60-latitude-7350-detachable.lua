-- omarchy-latitude-7350-detachable: Hyprland settings for the Dell Latitude 7350
-- Detachable only. Linked into ~/.config/hypr/extras/ by install.sh; loads after
-- omarchy-tablet's 50-tablet.lua, so it can override it.

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

-- No window transparency. Omarchy's default opacity (0.985 active / 0.96
-- inactive; browsers 1.0 / 0.985) showed as light-leak-like artifacts in
-- Chromium on this panel. This rule loads after Omarchy's, so it wins.
o.window(".*", { opacity = "1 1" })
