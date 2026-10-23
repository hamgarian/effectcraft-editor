"""Check the seams where a re-rendered range meets untouched frames: a jump (a change far bigger than the motion
around it), a repeated frame (no change where things move) or a missing frame (a gap in the numbering).

  python joincheck.py SEQ_DIR --joins 59,120 [--window 4] [--pattern f_%05d.png]
Use after re-rendering frames A..B: --joins A,B+1. Every-frame tools approve ranges; this approves the seams.
"""
import os
import sys

import cv2
import numpy as np

a = sys.argv[1:]


def opt(k, d):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d


joins = [int(x) for x in opt("--joins", "").split(",") if x]
win, pat = int(opt("--window", "4")), opt("--pattern", "f_%05d.png")
if len(a) != 1 or not joins:
    sys.exit(__doc__)
seq = a[0]


def load(n):
    p = os.path.join(seq, pat % n)
    if not os.path.exists(p):
        return None
    return cv2.cvtColor(cv2.resize(cv2.imread(p), (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.int16)


bad = 0
for j in joins:
    fr = {n: load(n) for n in range(j - win - 1, j + win + 1)}
    missing = [n for n, f in fr.items() if f is None and n >= 0]
    if missing:
        print(f"join f{j}: MISSING frames {missing}"); bad += 1; continue
    diff = {n: float(np.abs(fr[n] - fr[n - 1]).mean()) for n in range(j - win, j + win + 1) if n - 1 in fr and fr[n - 1] is not None}
    seam = diff.get(j, 0.0)
    around = np.median([v for n, v in diff.items() if n != j]) if len(diff) > 1 else 0.0
    if around > 1.0 and seam < 0.2 * around:
        verdict = "REPEATED frame (no change where the neighbours move)"; bad += 1
    elif seam > max(3.0 * around, around + 8.0):
        verdict = "JUMP (change much bigger than the motion around it)"; bad += 1
    else:
        verdict = "ok"
    print(f"join f{j}: seam diff {seam:.1f} vs neighbours {around:.1f} -> {verdict}")
print("seams clean" if bad == 0 else f"{bad} bad seam(s)")
sys.exit(1 if bad else 0)
