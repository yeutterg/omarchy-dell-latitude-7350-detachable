#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Capture a timed IR burst; compare single, mean, median, and aligned frames."""
import argparse
import configparser
from pathlib import Path
import time
import json
import cv2
import numpy as np
from dell_ir_reader import ir_libcamera_reader

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
p.add_argument('--seconds',type=float,default=10)
p.add_argument('--gain',type=int,default=32)
p.add_argument('--exposure',type=int,default=12000)
p.add_argument('--yunet',type=Path,required=True)
p.add_argument('--config',type=Path,default=Path('/etc/dell-face-auth/config.ini'))
a=p.parse_args()
if not 1<=a.seconds<=10:p.error('Duration must be 1..10 seconds')
a.output.mkdir(parents=True,exist_ok=True)
c=configparser.ConfigParser();c.read(a.config)
c.set('video','ir_gain',str(a.gain));c.set('video','ir_exposure',str(a.exposure));c.set('video','ir_auto_exposure','false')
r=ir_libcamera_reader(c);frames=[];start=time.monotonic()
try:
    while time.monotonic()-start<a.seconds:
        raw=r._raw()
        if raw is None:break
        frames.append(raw.copy())
finally:r.release()
print('CAPTURE DONE — you can relax.',len(frames),'frames',flush=True)
if len(frames)<12:raise RuntimeError('Insufficient frames for temporal comparison')
# Discard initial queued frames. Store only local diagnostic captures, not models.
frames=frames[4:];np.save(a.output/'raw-frames.npy',np.stack(frames))
cv2.setNumThreads(4)
y=cv2.FaceDetectorYN.create(str(a.yunet),'',(640,480),.6,.3,5000)
clahe=cv2.createCLAHE(2.,(8,8));rows=[]
def gray(raw):
    roi=raw[96:384,192:448];low=max(64,float(np.percentile(roi,1)));high=max(low+16,float(np.percentile(roi,99)))
    return np.clip((raw.astype(np.float32)-low)*255/(high-low),0,255).astype('uint8')
for index in range(0,len(frames)-7,8):
    block=np.stack(frames[index:index+8]);reference=gray(block[4]);g=[gray(f) for f in block]
    aligned=[];xx,yy=np.meshgrid(np.arange(640,dtype=np.float32),np.arange(480,dtype=np.float32))
    for f in g:
        flow=cv2.calcOpticalFlowFarneback(reference,f,None,.5,3,25,3,7,1.5,0)
        aligned.append(cv2.remap(f,xx+flow[:,:,0],yy+flow[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT))
    variants={'single':reference,'mean4':gray(np.mean(block[2:6],axis=0)),
        'mean8':gray(np.mean(block,axis=0)),'median8':gray(np.median(block,axis=0)),
        'aligned8':np.mean(aligned,axis=0).astype('uint8')}
    for variant,img in variants.items():
        for denoise in [False,True]:
            t=time.perf_counter();f=cv2.fastNlMeansDenoising(img,None,20,7,21) if denoise else img
            f=clahe.apply(f);bgr=cv2.cvtColor(f,cv2.COLOR_GRAY2BGR);_,faces=y.detect(bgr)
            name=f'{index:03d}-{variant}'+('-denoise' if denoise else '')
            cv2.imwrite(str(a.output/(name+'.png')),bgr)
            rows.append(dict(name=name,variant=variant,denoise=denoise,
                scores=[] if faces is None else faces[:,-1].tolist(),
                boxes=[] if faces is None else faces[:,:4].tolist(),
                processing_ms=round((time.perf_counter()-t)*1000,2)))
    print('Analyzed block',index,flush=True)
(a.output/'results.json').write_text(json.dumps(rows,indent=2))
print('Analysis complete',flush=True)
