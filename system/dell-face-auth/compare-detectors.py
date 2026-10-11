#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline detector comparison; never enrolls or changes authentication."""
import argparse
import json
from pathlib import Path
import time
import cv2
import dlib
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('captures', type=Path)
parser.add_argument('--yunet', type=Path, required=True)
parser.add_argument('--haar', type=Path)
parser.add_argument('--cnn', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
cv2.setNumThreads(4)
hog = dlib.get_frontal_face_detector()
haar = cv2.CascadeClassifier(str(args.haar)) if args.haar and hasattr(cv2, 'CascadeClassifier') else None
yunet = cv2.FaceDetectorYN.create(str(args.yunet), '', (640, 480), .6, .3, 5000)
cnn = dlib.cnn_face_detection_model_v1(str(args.cnn)) if args.cnn else None
clahe = cv2.createCLAHE(2., (8, 8))
rows = []
for path in sorted(args.captures.glob('[0-9][0-9]-gain*-exposure*.png')):
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    variants = {
        'original': gray,
        'denoise20': cv2.fastNlMeansDenoising(gray, None, 20, 7, 21),
        'denoise35': cv2.fastNlMeansDenoising(gray, None, 35, 7, 21),
        'median3': cv2.medianBlur(gray, 3),
        'denoise20_clahe': clahe.apply(cv2.fastNlMeansDenoising(gray, None, 20, 7, 21)),
    }
    for variant, image in variants.items():
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        for method in ['hog', 'yunet'] + (['haar'] if haar else []) + (['cnn'] if cnn and variant == 'original' else []):
            start = time.perf_counter()
            if method == 'hog':
                found = hog(image, 1)
                boxes = [[r.left(), r.top(), r.width(), r.height()] for r in found]
                scores = []
            elif method == 'haar':
                found = haar.detectMultiScale(image, 1.1, 5, minSize=(50, 50))
                boxes = [list(map(int, r)) for r in found]
                scores = []
            elif method == 'yunet':
                yunet.setInputSize((image.shape[1], image.shape[0]))
                _, found = yunet.detect(bgr)
                boxes = [] if found is None else found[:, :4].tolist()
                scores = [] if found is None else found[:, -1].tolist()
            else:
                found = cnn(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), 0)
                boxes = [[r.rect.left(), r.rect.top(), r.rect.width(), r.rect.height()] for r in found]
                scores = [r.confidence for r in found]
            elapsed = (time.perf_counter()-start)*1000
            rows.append(dict(image=path.name, variant=variant, detector=method,
                             milliseconds=round(elapsed, 2), boxes=boxes, scores=scores))
    print(path.name, ' '.join(f"{r['detector']}:{len(r['boxes'])}" for r in rows
          if r['image'] == path.name and r['variant'] == 'original'), flush=True)
args.output.write_text(json.dumps(rows, indent=2))
for method in sorted({r['detector'] for r in rows}):
    selected = [r for r in rows if r['detector'] == method and r['variant'] == 'original']
    print(method, 'original images detected', sum(bool(r['boxes']) for r in selected),
          '/', len(selected), 'median ms', round(float(np.median([r['milliseconds'] for r in selected])), 2))
