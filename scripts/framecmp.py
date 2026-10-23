"""Frame-by-frame comparison of the reference vs my render (same frame rate; read from ORIGINAL).

Reports: (1) cut timing in each video and the offset between matching cuts,
(2) frames whose overall brightness or colour differ most (palette / exposure mistakes),
(3) runs of frames where one video has a cut/flash the other lacks.
Usage: python framecmp.py ORIGINAL.mp4 MINE.mp4
"""
import sys
import cv2
import numpy as np


def stats(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        s = cv2.resize(f, (96, 96), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(s, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        out.append({"lum": float(cv2.cvtColor(s, cv2.COLOR_BGR2GRAY).mean()),
                    "rgb": s.reshape(-1, 3).mean(0)[::-1], "hist": hist})
    return out


def cuts(st, thr=0.45):
    c = []
    for i in range(1, len(st)):
        d = cv2.compareHist(st[i - 1]["hist"], st[i]["hist"], cv2.HISTCMP_BHATTACHARYYA)
        if d > thr:
            c.append(i)
    return c


def main():
    fps = cv2.VideoCapture(sys.argv[1]).get(cv2.CAP_PROP_FPS) or 20
    win = max(1, round(fps / 2))
    o, m = stats(sys.argv[1]), stats(sys.argv[2])
    n = min(len(o), len(m))
    co, cm = cuts(o), cuts(m)
    print(f"frames: original {len(o)}, mine {len(m)}")
    print("\nCUTS (frame)  original -> nearest in mine (offset in frames)")
    for c in co:
        near = min(cm, key=lambda x: abs(x - c)) if cm else None
        off = (near - c) if near is not None else None
        flag = "" if off is not None and abs(off) <= 1 else "   <-- MISMATCH"
        print(f"  {c:3d} ({c/fps:5.2f}s) -> {near} ({'n/a' if off is None else f'{off:+d}'}){flag}")
    extra = [c for c in cm if all(abs(c - x) > 1 for x in co)]
    print("  cuts only in mine:", ", ".join(f"{c} ({c/fps:.2f}s)" for c in extra) or "none")

    print("\nBRIGHTNESS / COLOUR per 0.5s window (orig vs mine, mean luma 0-255, mean RGB)")
    for w in range(0, n, win):
        a, b = o[w:w + win], m[w:w + win]
        lo, lm = np.mean([x["lum"] for x in a]), np.mean([x["lum"] for x in b])
        ro, rm = np.mean([x["rgb"] for x in a], 0), np.mean([x["rgb"] for x in b], 0)
        dcol = float(np.linalg.norm(ro - rm))
        flag = "  <-- exposure" if abs(lo - lm) > 30 else ("  <-- colour" if dcol > 45 else "")
        print(f"  {w/fps:5.2f}-{(w+win)/fps:5.2f}s  luma {lo:5.0f} / {lm:5.0f}   rgb {ro.astype(int)} / {rm.astype(int)}{flag}")


if __name__ == "__main__":
    main()
