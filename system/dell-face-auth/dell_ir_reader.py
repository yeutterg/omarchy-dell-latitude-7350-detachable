# SPDX-License-Identifier: GPL-2.0-only
"""On-demand OG0VA1B raw capture with continuous center-weighted exposure."""
import atexit
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np


class ir_libcamera_reader:
    """OpenCV-compatible reader for Howdy's recording_plugin interface."""

    def __init__(self, config):
        self.width, self.height = 640, 480
        self.proc = None
        self.original = None
        self.subdev = None
        self.frames = 0
        self.settled = False
        self.last_adjustment = 0.0
        self.last_adjustment_frame = -8
        self.gain = config.getint('video', 'ir_gain', fallback=16)
        self.exposure = config.getint('video', 'ir_exposure', fallback=2000)
        self.auto = config.getboolean('video', 'ir_auto_exposure', fallback=True)
        self.black = config.getint('video', 'ir_black_level', fallback=64)
        self.target = config.getint('video', 'ir_target', fallback=256)
        self.max_exposure = config.getint('video', 'ir_max_exposure', fallback=12000)
        self.verbose = config.getboolean('video', 'ir_verbose', fallback=False)
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        binary = config.get('video', 'ir_grab_path', fallback='/usr/local/libexec/dell-ir-grab')
        camera = config.get('video', 'ir_camera', fallback=r'\_SB_.PC00.LNK0')
        duration = max(15, config.getint('video', 'timeout', fallback=10) + 5)
        if not 16 <= self.gain <= 511 or not 1 <= self.exposure <= 12000:
            raise ValueError('Invalid initial OG0VA1B exposure or gain')
        if not 2000 <= self.max_exposure <= 12000 or not 128 <= self.target <= 512:
            raise ValueError('Invalid automatic exposure limits')
        for name in sorted(Path('/sys/class/video4linux').glob('v4l-subdev*/name')):
            if name.read_text().startswith('og0va1b'):
                self.subdev = '/dev/' + name.parent.name
                break
        if not self.subdev:
            raise RuntimeError('OG0VA1B sensor is not bound')
        original = subprocess.check_output(['v4l2-ctl', '-d', self.subdev, '--get-ctrl',
            'exposure,analogue_gain,vertical_blanking'], text=True)
        self.original = {k: int(v) for k, v in
                         (line.split(':') for line in original.splitlines())}
        try:
            self._controls(vertical_blanking=max(1616, self.exposure+14-480))
            self.proc = subprocess.Popen([binary, '--camera', camera, '--gain', str(self.gain),
                '--exposure', str(self.exposure), '--frames', '0', '--max-seconds', str(duration)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=0, env={**os.environ, 'LIBCAMERA_LOG_LEVELS': '*:FATAL'})
            atexit.register(self.release)
        except BaseException:
            self.release()
            raise

    def _controls(self, **values):
        subprocess.run(['v4l2-ctl', '-d', self.subdev, '--set-ctrl',
            ','.join(f'{key}={value}' for key, value in values.items())],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def _raw(self):
        if not self.proc or not self.proc.stdout:
            return None
        data = bytearray(614400)
        position = 0
        while position < len(data):
            count = self.proc.stdout.readinto(memoryview(data)[position:])
            if not count:
                return None
            position += count
        return np.frombuffer(data, dtype='<u2').reshape(480, 640)

    @staticmethod
    def next_settings(exposure, gain, level, clipped, target, black, maximum):
        ratio = min(2.0, max(.5, (target-black)/max(float(level)-black, 1)))
        if clipped >= .02:
            ratio = min(ratio, .5)
        product = min(maximum*511, max(16, exposure*gain*ratio))
        # Hold a modest gain (8x) until available exposure is exhausted.
        next_exposure = max(1, min(maximum, round(product/128)))
        next_gain = max(16, min(511, round(product/next_exposure)))
        return next_exposure, next_gain

    def read(self):
        raw = self._raw()
        if raw is None:
            return False, None
        self.frames += 1
        region = raw[96:384:2, 192:448:2]
        level = float(np.percentile(region, 80))
        clipped = float(np.mean(region >= 1000))
        self.settled = .85*self.target <= level <= 1.15*self.target and clipped < .02
        now = time.monotonic()
        if self.auto and not self.settled and self.frames > 4 and self.frames-self.last_adjustment_frame >= 8 and now-self.last_adjustment >= .2:
            exposure, gain = self.next_settings(self.exposure, self.gain, level, clipped,
                                                self.target, self.black, self.max_exposure)
            if (exposure, gain) != (self.exposure, self.gain):
                # Expand the allowed exposure first; shrink it after exposure changes.
                if exposure > self.exposure:
                    self._controls(vertical_blanking=max(1616, exposure+14-480))
                self._controls(exposure=exposure, analogue_gain=gain)
                if exposure < self.exposure:
                    self._controls(vertical_blanking=max(1616, exposure+14-480))
                self.exposure, self.gain = exposure, gain
                self.last_adjustment = now
                # Drain queued sensor/ISP frames before metering this setting.
                self.last_adjustment_frame = self.frames
                if self.verbose:
                    import sys
                    print(f'IR AE: p80={level:.0f}, exposure={exposure}, gain={gain}', file=sys.stderr)
        low = max(self.black, float(np.percentile(region, 1)))
        high = max(low+16, float(np.percentile(region, 99)))
        gray = np.clip((raw.astype(np.float32)-low)*(255/(high-low)), 0, 255).astype(np.uint8)
        gray = self.clahe.apply(gray)
        return True, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def grab(self):
        result, _ = self.read()
        return result

    def set(self, prop, value):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return int(value) == 640
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return int(value) == 480
        return False

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: 640., cv2.CAP_PROP_FRAME_HEIGHT: 480.}.get(prop, 0.)

    def release(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
            for pipe in (self.proc.stdout, self.proc.stderr):
                if pipe:
                    pipe.close()
            self.proc = None
        if self.original:
            original, self.original = self.original, None
            try:
                self._controls(vertical_blanking=max(original['vertical_blanking'],
                                                    original['exposure']+14-480))
                self._controls(exposure=original['exposure'], analogue_gain=original['analogue_gain'])
                self._controls(vertical_blanking=original['vertical_blanking'])
            finally:
                atexit.unregister(self.release)
