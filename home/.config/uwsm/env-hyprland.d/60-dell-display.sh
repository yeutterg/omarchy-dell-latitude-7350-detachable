# Temporary display-artifact diagnostic for the Latitude 7350 Detachable.
# Force simpler compositor buffers to test Intel MTL compressed scanout.
# Takes effect on the next desktop session; ordinary config reload is insufficient.
# Remove this file/link and log in again to restore the default allocation path.
export AQ_NO_MODIFIERS=1
export HYPRLAND_EGL_NO_MODIFIERS=1
