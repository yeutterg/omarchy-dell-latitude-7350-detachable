# Dell IR face authentication integration (in progress)

The OG0VA1B IR sensor is streaming. The root-owned recognition runtime is installed under `/opt/dell-face-auth`.
Authentication is not enabled and no face model is enrolled yet. The corrected gain driver (DKMS 0.2) is installed
and automatic exposure converges to its target. Active illumination is unresolved.

`ir-grab.cpp` is adapted from `bamarc/dragonfly-folio-camera-mod`, commit
`8f3cb092de3168b4c4af077fdd506c0bb7ed80c2`, under GPL-2.0. The Dell defaults
select `\_SB_.PC00.LNK0`, use gain 16, and do not configure an HP torch.
Output is 640x480 little-endian 16-bit containers holding monochrome 10-bit
samples. A timeout and parent death signal bound each capture. Nonblocking
output ensures a stalled consumer cannot defeat timeout or signal cleanup.

`dell_ir_reader.py` implements Howdy's recorder interface. It meters the
central region, adjusts real sensor exposure/gain continuously, limits exposure
to roughly 100 ms, normalizes the grayscale image, and restores camera controls
when capture ends. It does not fall back to the RGB sensor. The optional HP
time-of-flight check is not imported because this Dell has no verified matching
hardware.

Local validation on 2026-10-10:

- Native helper compiled against libcamera 0.7.2.
- Reader captured 85 frames in four seconds and adjusted exposure/gain live.
- Dark, bright/clipped, and maximum-setting exposure decisions checked.
- Corrected-gain live capture now waits eight frames after each adjustment
  to drain stale sensor/ISP buffers. A ten-second run captured 112 frames
  and settled at exposure 4000/gain 128 without the previous oscillation.
  No face was detected while the subject was at the left edge of the frame.
- A consumer that never reads stdout did not hang capture: the two-second
  timeout exited in 2.12 seconds and restored the original gain/exposure.
- Python dependencies and dlib recognition models are installed in the
  root-owned `/opt/dell-face-auth` runtime, isolated from the system interpreter.
- The installed comparison process rejects missing enrollment with exit 10.

Prepared Howdy upstream source is pinned to
`d3ab99382f88f043d15f15c1450ab69433892a1c` (MIT) in `/tmp/dell-howdy-source`.
Its PAM module compiled with paths under `/opt/dell-face-auth`, config under
`/etc/dell-face-auth`, and models under `/var/lib/dell-face-auth`. Production
code, interpreter, and configuration are root-owned; future templates will
be root-owned and readable by your user. The user-owned development environment
is not used by privileged PAM flows.

The intended desktop flow is a separate `omarchy-lock-face` PAM service running
alongside Omarchy's existing password flow. A `dell.lock` clone is staged in
`home/.config/omarchy/plugins/`, based on the installed `tablet.lock` plugin
and retaining its PIN keypad. It has not replaced the active lock plugin.
Its face flow starts only after the compositor secures the session, pauses
when the display blanks, retries while awake, and cancels when another flow
unlocks. Activate after enrollment and positive/negative authentication tests.

A centered-face test on 2026-10-10 captured 92 frames, settled at exposure
5224/gain 128, and detected no face. Spatial denoising and a 12000-line
exposure at gain 64 also failed detection. Enrollment has therefore not
been attempted; exposure convergence alone does not establish usable imagery.

Remaining verification: resolve/test the emitter, verify face detection,
enroll your face, test matching and rejection,
install the dedicated PAM service, integrate the lock flow, and exercise
unlock/fallback plus suspend/resume and reboot persistence.

Exposure/gain sweep (2026-10-10): captured 16 settings with gains
16/32/64/128/256/511 and exposures 1000..16000 lines. Gain 32/exposure
16000 produced the cleanest central-face detail; at roughly equal sensor
brightness, the preview noise measure increased from 10 at gain 32/exposure
16000 to 14 at gain 64/exposure 8000 and 18 at gain 128/exposure 4000.
The measure is median absolute difference from a 5x5 spatial median in a
fixed central face crop; it is comparative, not calibrated sensor read noise.
The subject moved slightly across captures. Every image failed the HOG face
detector, including denoised variants. Higher gain 256 behaved nonlinearly:
it produced less signal than gain 128 at the same exposure, so nominal gain
values above 128 need separate validation. User captures and the comparison
sheet remain under `/tmp/dell-ir-settings`, outside this repository.

A second, CNN detector (`davisking/dlib-models`' official pretrained model)
detected one face in gain 32/exposure 16000 with confidence 0.313, taking
3.03 seconds on the CPU. It found no face in gain 64/exposure 16000 or
gain 32/exposure 8000. This is a promising diagnostic result, not a
recognition match or proof of reliable authentication.

Detector and recognizer comparison on the saved sweep:

| Approach | Correct face locations in 16 images | Approximate CPU detection time |
| --- | --- | --- |
| dlib HOG (existing Howdy default) | 0 | 78 ms |
| dlib CNN, original preview | 1 | 2.9 s |
| YuNet, original preview | 0 | 7.5 ms |
| YuNet, denoise 20 + CLAHE | 2 | 7.5 ms plus preprocessing |
| Haar cascade | 0; shoulder/background false positives | 14–28 ms |
| ResNet-10 SSD | 0; one oversized false positive | 17 ms |

YuNet's two detection scores were 0.773 and 0.734 at an exploratory 0.6
cutoff, below OpenCV's example default of 0.85. Lowering a diagnostic
detection cutoff is not a reason to relax authentication acceptance. Both
YuNet and HOG detected the known-good OpenCV sample; Haar/SSD also passed
that control. Spatial denoising helped YuNet but usually hurt dlib CNN.

The two useful YuNet crops gave dlib descriptor distance 0.420 (fails the
current strict Howdy threshold 0.35), versus SFace cosine similarity 0.390.
SFace's example LFW cutoff is 0.363, so this pair nominally passes that
example, but the margin is small and the cutoff is not validated for this
IR sensor. Similarities against a different-person public sample were
0.159 and 0.146. This is only an offline consistency check, not completed
enrollment, a live rejection test, or authentication validation. SFace
feature extraction took 7–11 ms, compared with dlib's 119–122 ms.

`compare-detectors.py` records detector boxes, scores, and timings without
enrolling anything. Models must be supplied explicitly. OpenCV 5 removed
the legacy cascade/Caffe APIs in this environment;
`compare-legacy-detectors.py` runs those comparisons in a separate OpenCV
4.x scratch environment, without changing the installed authentication
runtime. Models are from official OpenCV/dlib repositories and remain
outside this repository:

- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
- https://github.com/opencv/opencv/tree/4.x/samples/dnn/face_detector
- https://github.com/davisking/dlib-models

The promising next experiment is low-gain capture with temporally averaged
raw frames, followed by YuNet/SFace. The original IR sensor is retained.
The UVC `linux-enable-ir-emitter` project explicitly excludes MIPI/IPU6
sensors, so it does not supply this machine's missing illumination control:
https://github.com/EmixamPP/linux-enable-ir-emitter

`benchmark-models.json` records tested model URLs and SHA-256 digests of
the final local model files. `compare-burst.py` prepares a bounded
10-second raw capture experiment comparing single frames, averages of
four/eight frames, temporal median, and optical-flow-aligned averaging.
It prints capture completion before offline analysis and restores camera
controls. The live comparison captured 104 frames in ten seconds; results follow.

Live burst comparison: gain 32/exposure 12000, 104 captured frames, four
initial frames discarded, 12 eight-frame blocks compared. Camera controls
restored to exposure 554/gain 16/vblank 1616 afterward.

| Processing | Face detected in blocks | Maximum YuNet score |
| --- | --- | --- |
| Single frame | 0/12 | below exploratory 0.6 cutoff |
| Single + denoise 20 + CLAHE | 12/12 | 0.814 |
| Mean of four + denoise 20 + CLAHE | 12/12 | 0.830 |
| Mean of eight + denoise 20 + CLAHE | 12/12 | 0.828 |
| Median of eight + denoise 20 + CLAHE | 12/12 | 0.827 |
| Optical-flow-aligned eight, CLAHE only | 8/12 | 0.718 |
| Optical-flow-aligned eight + denoise + CLAHE | 12/12 | 0.814 |

Denoised pipeline processing took about 103 ms, excluding temporal capture
latency and optical-flow alignment. None of these detection scores reached
the example 0.85 cutoff. Frame averaging alone mostly failed detection;
spatial denoising is essential for this particular capture.

Using one four-frame average as an offline SFace reference, other
four-frame averages gave cosine similarities 0.592..0.834 (median 0.666),
whereas single frames ranged 0.206..0.891 (median 0.563). Two earlier
captures, processed identically without diagnostic bounding-box overlays,
matched at 0.418 and 0.390; a different-person control was 0.006. These
are diagnostic features held in memory, not saved authentication templates.
The same-burst results support four-frame averaging; the cross-capture
margins still need testing across lighting, motion, and actual nonmatching
subjects. No PAM service or lock flow was enabled. Full artifacts remain
under `/tmp/dell-ir-burst`.
