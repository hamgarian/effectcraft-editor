"""Find frames where pure black shows at the frame borders (a shot's edge exposed over the empty timeline).
Usage: python edgeblack.py SEQ_DIR [--fps=N] [REF.mp4]
Measures the share of near-black pixels (all channels < 12) in a 40 px border band per frame and lists
the worst frames; with REF, prints the reference's value for the same frame so intentional black isn't flagged.
"""
import sys, glob, re
import cv2
import numpy as np

FPS = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--fps=')), 20))
sys.argv = [a for a in sys.argv if not a.startswith('--fps=')]


def border_black(img):
    h, w = img.shape[:2]; b = 40
    band = np.concatenate([img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3), img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)])
    return float((band.max(axis=1) < 12).mean())


files = sorted(glob.glob(sys.argv[1] + "/f_*.png"))
ref = []
if len(sys.argv) > 2:
    cap = cv2.VideoCapture(sys.argv[2])
    while True:
        ok, f = cap.read()
        if not ok:
            break
        ref.append(border_black(f))
rows = []
for f in files:
    n = int(re.search(r"f_(\d+)", f).group(1))
    m = border_black(cv2.imread(f))
    r = ref[n] if n < len(ref) else 0.0
    if m - r > 0.05:
        rows.append((m - r, n, m, r))
rows.sort(reverse=True)
print(f"frames with exposed black border (mine minus ref > 5%): {len(rows)}")
for d, n, m, r in rows[:20]:
    print(f"  f{n:03d} {n/FPS:5.2f}s  mine {m:5.1%}  ref {r:5.1%}")
