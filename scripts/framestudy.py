"""Frame-by-frame study sheet + eyedropper.
Usage: python framestudy.py VIDEO OUT.png F0 F1 [--w 360] [--pick x,y x,y ...]
Writes a labelled grid of frames F0..F1 (inclusive). With --pick, prints the RGB hex at each (x,y) of the
full-resolution frame F0 (eyedropper), and the letterbox: rows at top/bottom that are near-black in every frame.
"""
import sys
import cv2
import numpy as np

args = sys.argv[1:]
w = int(args[args.index("--w") + 1]) if "--w" in args else 360
picks = []
if "--pick" in args:
    i = args.index("--pick"); picks = [tuple(map(int, p.split(","))) for p in args[i + 1:]]; args = args[:i]
args = [a for k, a in enumerate(args) if a != "--w" and (k == 0 or args[k - 1] != "--w")]
video, out, f0, f1 = args[0], args[1], int(args[2]), int(args[3])
cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS) or 20; frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
sel = frames[f0:f1 + 1]
H, W = sel[0].shape[:2]
# letterbox: rows that are near-black (max < 20) in every selected frame
dark = np.all([f.max(axis=(1, 2)) < 20 for f in sel], axis=0)
top = int(np.argmin(dark)) if dark[0] else 0
bot = int(np.argmin(dark[::-1])) if dark[-1] else 0
print(f"frame {W}x{H}; black bars: top {top}px, bottom {bot}px -> active picture {W}x{H - top - bot} (aspect {W / max(1, H - top - bot):.3f})")
for (x, y) in picks:
    b, g, r = sel[0][y, x]
    print(f"  pick f{f0} ({x},{y}) = #{r:02x}{g:02x}{b:02x}")
tiles = []
for k, f in enumerate(sel):
    t = cv2.resize(f, (w, int(H * w / W)), interpolation=cv2.INTER_AREA)
    cv2.rectangle(t, (0, 0), (w, 16), (0, 0, 0), -1)
    cv2.putText(t, f"f{f0 + k}  {(f0 + k) / fps:.2f}s", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    tiles.append(t)
cols = 5
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)]))
print(out)
