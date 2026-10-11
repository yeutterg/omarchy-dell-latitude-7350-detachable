#!/usr/bin/env bash
# Install staged code only. This does not enroll a model or enable a PAM flow.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run this installer through system authentication.' >&2; exit 1; }
repo=/home/greg/dotfiles/omarchy-dell-latitude-7350-detachable/system/dell-face-auth
stage=/tmp/dell-face-auth-stage/howdy
runtime=/home/greg/.local/share/dell-face-auth
[[ -f $stage/recorders/dell_ir_reader.py && -f /tmp/dell-howdy-build/pam_dell_howdy.so ]]
[[ ! -e /opt/dell-face-auth ]] || { echo '/opt/dell-face-auth already exists; inspect before replacing.' >&2; exit 1; }
install -d -m 755 /opt/dell-face-auth /etc/dell-face-auth /usr/local/lib/security
cp -a "$runtime/venv" /opt/dell-face-auth/venv
cp -a "$runtime/dlib-data" /opt/dell-face-auth/dlib-data
cp -a "$stage" /opt/dell-face-auth/howdy
chown -R root:root /opt/dell-face-auth
chmod -R go-w /opt/dell-face-auth
install -m 644 "$repo/config.ini" /etc/dell-face-auth/config.ini
install -m 755 /tmp/dell-howdy-build/pam_dell_howdy.so /usr/local/lib/security/pam_dell_howdy.so
install -Dm755 "$repo/dell-ir-grab" /usr/local/libexec/dell-ir-grab
install -d -m 750 -o root -g greg /var/lib/dell-face-auth/models
install -d -m 700 /var/log/dell-face-auth
cat > /usr/local/bin/dell-howdy <<'CLI'
#!/usr/bin/env bash
exec /opt/dell-face-auth/venv/bin/python /opt/dell-face-auth/howdy/cli.py "$@"
CLI
chmod 755 /usr/local/bin/dell-howdy
# Prove the copied interpreter and compiled dependencies load at their final paths.
/opt/dell-face-auth/venv/bin/python -c 'import cv2, numpy, dlib; print("Face-recognition runtime installed")'
echo 'No login or lock PAM stack has been changed. Enroll and validate before enabling.'
