"""Find isolated odd frames in a rendered sequence: frame i differs strongly from both i-1 and i+1
while i-1 and i+1 resemble each other (a one-frame pop, not a cut).
Usage: python glitchfind.py SEQ_DIR [--fps=N]
"""
import sys, glob
import cv2
import numpy as np

FPS = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--fps=')), 20))
sys.argv = [a for a in sys.argv if not a.startswith('--fps=')]

files = sorted(glob.glob(sys.argv[1] + "/f_*.png"))
small = [cv2.resize(cv2.imread(f), (120, 120), interpolation=cv2.INTER_AREA).astype(np.float32) for f in files]


def d(a, b):
    return float(np.mean(np.abs(a - b)))


rows = []
for i in range(1, len(small) - 1):
    prev, cur, nxt = small[i - 1], small[i], small[i + 1]
    dp, dn, dpn = d(prev, cur), d(cur, nxt), d(prev, nxt)
    score = min(dp, dn) - dpn  # high when i is the odd one out
    if score > 12:
        rows.append((score, i, dp, dn, dpn))
rows.sort(reverse=True)
print("isolated odd frames (score, frame, time, diff-to-prev, diff-to-next, prev-vs-next):")
for s, i, dp, dn, dpn in rows[:25]:
    print(f"  {s:6.1f}  f{i:03d}  {i/FPS:5.2f}s  {dp:6.1f} {dn:6.1f} {dpn:6.1f}")
print(f"total flagged: {len(rows)}")
