"""Per-shot camera motion (pan / zoom / roll) for two videos, from frame-to-frame similarity transforms.

Usage: python camtrack.py ORIGINAL.mp4 MINE.mp4 shots.json [--curve name1,name2]
shots.json: [["name", t0, t1], ...] in seconds (required). Frame rate is read from ORIGINAL.
Dominant motion is estimated with ORB features + RANSAC (estimateAffinePartial2D), so a large
moving foreground object can bias a shot; numbers are camera-ish, not exact.
"""
import sys
import cv2
import numpy as np

FPS = 20  # replaced in main() by the reference video's frame rate
SHOTS = []


def frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(f, (540, 540)), cv2.COLOR_BGR2GRAY)
        out.append(cv2.GaussianBlur(g, (5, 5), 0))  # soften film grain so features lock to structure
    return out


ORB = cv2.ORB_create(1500)
BF = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def step(a, b):
    ka, da = ORB.detectAndCompute(a, None)
    kb, db = ORB.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 12 or len(kb) < 12:
        return None
    m = BF.match(da, db)
    if len(m) < 12:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None or inl is None or inl.sum() < 10:
        return None
    s = float(np.hypot(M[0, 0], M[1, 0]))
    r = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    return M[0, 2] * 2, M[1, 2] * 2, s, r  # pan in 1080px units


def shot_summary(fr, t0, t1):
    a, b = int(round(t0 * FPS)), int(round(t1 * FPS))
    zoom, rot, px, py, bad, jit = 1.0, 0.0, 0.0, 0.0, 0, []
    for i in range(a, min(b, len(fr) - 1)):
        st = step(fr[i], fr[i + 1])
        if st is None:
            bad += 1
            continue
        dx, dy, s, r = st
        zoom *= s; rot += r; px += dx; py += dy
        jit.append(np.hypot(dx, dy))
    shake = float(np.std(jit)) if jit else 0.0
    return zoom, rot, px, py, shake, bad


def curve(fr, t0, t1):
    """per-frame camera step: (dx, dy, scale, roll) for each frame pair in [t0, t1]"""
    a, b = int(round(t0 * FPS)), int(round(t1 * FPS))
    return [step(fr[i], fr[i + 1]) for i in range(a, min(b, len(fr) - 1))]


def fmt(st):
    if st is None:
        return "   --  "
    dx, dy, s, r = st
    return f"{dx:+5.0f},{dy:+5.0f} {s:4.2f} {r:+4.1f}"


def main():
    global SHOTS, FPS
    FPS = cv2.VideoCapture(sys.argv[1]).get(cv2.CAP_PROP_FPS) or 20
    if "--curve" in sys.argv:
        i = sys.argv.index("--curve"); want = sys.argv[i + 1].split(","); del sys.argv[i:i + 2]
        import json
        shots = [tuple(s) for s in json.load(open(sys.argv[3], encoding="utf-8"))]
        o, m = frames(sys.argv[1]), frames(sys.argv[2])
        for name, t0, t1 in shots:
            if name not in want:
                continue
            print(f"== {name} {t0}-{t1}s   per frame: pan dx,dy (px)  scale  roll(deg)   ORIGINAL | MINE")
            for k, (x, y) in enumerate(zip(curve(o, t0, t1), curve(m, t0, t1))):
                print(f"  {t0 + k / FPS:5.2f}  {fmt(x)} | {fmt(y)}")
        return
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    if len(sys.argv) > 3:
        import json
        SHOTS = [tuple(s) for s in json.load(open(sys.argv[3], encoding="utf-8"))]
    o, m = frames(sys.argv[1]), frames(sys.argv[2])
    print(f"{'shot':15} | {'ORIGINAL zoom  roll   panX   panY shake':40} | {'MINE zoom  roll   panX   panY shake':36}")
    for name, t0, t1 in SHOTS:
        zo, ro, xo, yo, so, bo = shot_summary(o, t0, t1)
        zm, rm, xm, ym, sm, bm = shot_summary(m, t0, t1)
        print(f"{name:15} | {zo:9.2f}x {ro:5.1f}d {xo:6.0f} {yo:6.0f} {so:5.1f}{'*' if bo else ' '}          "
              f"| {zm:5.2f}x {rm:5.1f}d {xm:6.0f} {ym:6.0f} {sm:5.1f}{'*' if bm else ' '}")
    print("zoom = total scale over the shot, roll = degrees, pan = px (frame scaled to 1080 wide; + = content moves right/down),"
          " shake = frame-to-frame jitter std px, * = some frames untrackable")


if __name__ == "__main__":
    main()
