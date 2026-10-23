"""Turn a reference video into a STYLE map you can build an original edit on: keep its pacing, camera language,
palette and energy; change the content. Writes a JSON map, a Markdown beat table (references/director.md columns,
pre-filled) and a contact sheet with one frame per shot.

  python stylemap.py REF.mp4 OUT_DIR [--max-shots 60]
Uses scripts/audio.py for tempo when the reference has sound.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

a = sys.argv[1:]
if len(a) < 2:
    sys.exit(__doc__)
ref, out = a[0], a[1]
max_shots = int(a[a.index("--max-shots") + 1]) if "--max-shots" in a else 60
os.makedirs(out, exist_ok=True)

cap = cv2.VideoCapture(ref); fps = cap.get(cv2.CAP_PROP_FPS) or 25
frames, small, diffs, prev = [], [], [], None
while True:
    ok, f = cap.read()
    if not ok:
        break
    s = cv2.resize(f, (160, int(160 * f.shape[0] / f.shape[1])), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY).astype(np.int16)
    diffs.append(0.0 if prev is None else float(np.abs(g - prev).mean())); prev = g
    small.append(s); frames.append(cv2.resize(f, (320, int(320 * f.shape[0] / f.shape[1]))))
if not small:
    sys.exit("no frames read")
d = np.array(diffs); thr = max(25.0, float(np.median(d[1:])) * 4)
cuts = [0] + [i for i in range(1, len(d)) if d[i] > thr and i - 1 not in ()] + [len(d)]
cuts = sorted(set(cuts))
shots = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] >= 1][:max_shots]
orb = cv2.ORB_create(500)


def camera(f0, f1):
    """scale / rotation / pan between a shot's first and last frame (similarity fit on ORB matches)"""
    a0, a1 = cv2.cvtColor(small[f0], cv2.COLOR_BGR2GRAY), cv2.cvtColor(small[f1], cv2.COLOR_BGR2GRAY)
    k0, d0 = orb.detectAndCompute(a0, None); k1, d1 = orb.detectAndCompute(a1, None)
    if d0 is None or d1 is None or len(k0) < 8 or len(k1) < 8:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d0, d1)
    if len(m) < 8:
        return None
    M, _ = cv2.estimateAffinePartial2D(np.float32([k0[x.queryIdx].pt for x in m]), np.float32([k1[x.trainIdx].pt for x in m]))
    if M is None:
        return None
    s = float(np.hypot(M[0, 0], M[1, 0])); r = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    k = frames[0].shape[1] / small[0].shape[1]
    return {"zoom": round(s, 3), "roll": round(r, 2), "pan_px": [round(float(M[0, 2]) * k * 4, 1), round(float(M[1, 2]) * k * 4, 1)]}


def describe(cam):
    if not cam:
        return "unmeasured (too little texture or a hard change)"
    parts = []
    if cam["zoom"] > 1.03: parts.append(f"push in x{cam['zoom']:.2f}")
    elif cam["zoom"] < 0.97: parts.append(f"pull out x{cam['zoom']:.2f}")
    if abs(cam["roll"]) > 1: parts.append(f"roll {cam['roll']:+.0f} deg")
    if max(abs(v) for v in cam["pan_px"]) > 20: parts.append("pan " + ("right" if cam["pan_px"][0] < 0 else "left") if abs(cam["pan_px"][0]) >= abs(cam["pan_px"][1]) else "pan " + ("down" if cam["pan_px"][1] < 0 else "up"))
    return ", ".join(parts) or "locked off"


def palette(f, k=4):
    px = cv2.resize(f, (64, 36)).reshape(-1, 3).astype(np.float32)
    _, lab, cen = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    order = np.argsort(-np.bincount(lab.ravel(), minlength=k))
    return ["#%02x%02x%02x" % tuple(int(c) for c in cen[i][::-1]) for i in order]


rows = []
for i, (s0, s1) in enumerate(shots):
    mid = (s0 + s1 - 1) // 2
    cam = camera(s0, max(s0, s1 - 1)) if s1 - s0 > 2 else None
    rows.append({"shot": i + 1, "start": round(s0 / fps, 2), "end": round(s1 / fps, 2), "frames": s1 - s0,
                 "camera": cam, "camera_words": describe(cam), "palette": palette(small[mid]),
                 "luma": round(float(cv2.cvtColor(small[mid], cv2.COLOR_BGR2GRAY).mean()), 1),
                 "energy": round(float(np.mean(d[s0 + 1:s1])) if s1 - s0 > 1 else 0.0, 1)})
lens = np.array([r["frames"] for r in rows])
summary = {"fps": fps, "duration": round(len(small) / fps, 2), "shots": len(rows), "median_shot_frames": int(np.median(lens)),
           "shortest": int(lens.min()), "longest": int(lens.max()), "cuts_per_second": round(len(rows) / (len(small) / fps), 2)}
has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", ref],
                           capture_output=True, text=True).stdout.strip()
if has_audio:
    import audio
    bpm, bt, hits = audio.beats(audio.decode(ref), audio.SR)
    marks = np.array(sorted(bt + hits))
    on = sum(1 for r in rows[1:] if len(marks) and np.min(np.abs(marks - r["start"])) * fps <= 1)
    summary.update({"bpm": round(bpm, 1), "cuts_on_beat": f"{on}/{max(1, len(rows) - 1)}", "beat_frames": round(fps * 60 / bpm, 1)})
json.dump({"summary": summary, "shots": rows}, open(os.path.join(out, "stylemap.json"), "w"), indent=1)

md = [f"# Style map: {os.path.basename(ref)}", "",
      f"{summary['shots']} shots in {summary['duration']} s ({summary['cuts_per_second']} cuts/s); median shot {summary['median_shot_frames']} frames "
      f"(shortest {summary['shortest']}, longest {summary['longest']})" + (f"; {summary['bpm']} BPM, {summary['cuts_on_beat']} cuts on a beat/hit" if has_audio else ""), "",
      "Keep: the rhythm (shot lengths), camera language and palette rows below. Change: subject, art, words.", "",
      "| time | frames | job | moving object | what changes | camera (measured) | palette | luma | energy |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['start']:.2f}-{r['end']:.2f} | {r['frames']} | | | | {r['camera_words']} | {' '.join(r['palette'])} | {r['luma']} | {r['energy']} |")
open(os.path.join(out, "stylemap.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
tiles = []
for r in rows:
    t = frames[(int(r["start"] * fps) + int(r["end"] * fps) - 1) // 2].copy()
    cv2.rectangle(t, (0, 0), (t.shape[1], 16), (0, 0, 0), -1)
    cv2.putText(t, f"{r['shot']}: {r['start']:.2f}s {r['frames']}f", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    tiles.append(t)
while len(tiles) % 6:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(os.path.join(out, "shots.png"), np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]))
print(json.dumps(summary))
print(os.path.join(out, "stylemap.md"))
