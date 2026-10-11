#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline legacy detectors; requires a separate OpenCV 4.x environment."""
import argparse
from pathlib import Path
import cv2,time,json,numpy as np
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('captures',type=Path)
parser.add_argument('--haar',type=Path,required=True)
parser.add_argument('--ssd-config',type=Path,required=True)
parser.add_argument('--ssd-model',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.captures;cv2.setNumThreads(4)
haar=cv2.CascadeClassifier(str(args.haar))
net=cv2.dnn.readNetFromCaffe(str(args.ssd_config),str(args.ssd_model));rows=[]
for p in [out/'detector-positive-control.jpg',*sorted(out.glob('[0-9][0-9]-gain*-exposure*.png'))]:
 f=cv2.imread(str(p),0)
 for v,a in [('original',f),('denoise20',cv2.fastNlMeansDenoising(f,None,20,7,21)),('denoise20_clahe',cv2.createCLAHE(2.,(8,8)).apply(cv2.fastNlMeansDenoising(f,None,20,7,21)))]:
  t=time.monotonic();h=haar.detectMultiScale(a,1.1,5,minSize=(50,50));rows.append(dict(image=p.name,variant=v,detector='haar',boxes=h.tolist() if len(h) else [],milliseconds=round((time.monotonic()-t)*1000,2)))
  t=time.monotonic();net.setInput(cv2.dnn.blobFromImage(cv2.cvtColor(a,cv2.COLOR_GRAY2BGR),1.,(300,300),(104.,177.,123.)));r=net.forward()[0,0];r=r[r[:,2]>.6];rows.append(dict(image=p.name,variant=v,detector='ssd',scores=r[:,2].tolist(),boxes=(r[:,3:7]*[a.shape[1],a.shape[0],a.shape[1],a.shape[0]]).tolist(),milliseconds=round((time.monotonic()-t)*1000,2)))
 print(p.name,'haar',len(h),'ssd',r[:,2].tolist(),flush=True)
args.output.write_text(json.dumps(rows,indent=2))
for method in ['haar','ssd']:
 for v in ['original','denoise20','denoise20_clahe']:
  a=[r for r in rows if r['detector']==method and r['variant']==v and r['image']!='detector-positive-control.jpg'];print(method,v,'detections',sum(bool(r['boxes']) for r in a),'median ms',round(float(np.median([r['milliseconds'] for r in a])),2))
