"""Every-frame comparison of a candidate against the reference: MAE, PSNR and SSIM per frame, the worst frames,
the frames around every reference cut (boundaries), and frames whose best match is a NEIGHBOURING reference frame
(the candidate leads or lags). Sampled sheets locate problems; this is what approves a range.
Usage: python framemetrics.py REF.mp4 MINE.mp4 [--ref-start N] [--mine-start N] [--count N]
                              [--width 320] [--max-offset 3] [--worst 6] [--out DIR]
Writes DIR/metrics.json and DIR/worst.png (ref | mine | difference heat map) when --out is given.
--baseline: re-encode the reference with the candidate's codec and bitrate and measure ref vs that copy: the codec's
own error (noise floor). Candidate frames within floor + 1 are marked codec-level, not a mismatch (exact-replay work).
"""
import json
import os
import sys

import cv2
import numpy as np


def opt(name, default, cast=int):
    if name in sys.argv:
        i = sys.argv.index(name); v = cast(sys.argv[i + 1]); del sys.argv[i:i + 2]; return v
    return default


ref_start, mine_start, count = opt("--ref-start", 0), opt("--mine-start", 0), opt("--count", 0)
width, max_off, n_worst, out = opt("--width", 320), opt("--max-offset", 3), opt("--worst", 6), opt("--out", "", str)
baseline = "--baseline" in sys.argv
if baseline:
    sys.argv.remove("--baseline")
if len(sys.argv) != 3:
    sys.exit(__doc__)


def frames(path, start, n, w):
    cap = cv2.VideoCapture(path); fs = []; i = 0
    while True:
        ok, f = cap.read()
        if not ok or (n and len(fs) >= n):
            break
        if i >= start:
            h = int(f.shape[0] * w / f.shape[1])
            fs.append(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA))
        i += 1
    return fs


def ssim(a, b):
    """mean SSIM on grey images (Wang et al. 2004, 11x11 Gaussian window, sigma 1.5)"""
    a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float64); b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = g(a), g(b)
    va, vb, cov = g(a * a) - ma * ma, g(b * b) - mb * mb, g(a * b) - ma * mb
    return float((((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))).mean())


def mae(a, b):
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


ref = frames(sys.argv[1], ref_start, count + max_off if count else 0, width)
mine = frames(sys.argv[2], mine_start, count, width)
n = min(len(mine), len(ref), count or 10 ** 9)
if n == 0:
    sys.exit("no frames to compare (check the start frames and paths)")
if len(ref) != len(mine) and not count:
    print(f"frame count differs: ref {len(ref)}, mine {len(mine)} (comparing the first {n})")
rows = []
for i in range(n):
    m = mae(ref[i], mine[i])
    psnr = 99.0 if m == 0 else float(cv2.PSNR(ref[i], mine[i]))
    best_k, best = 0, m
    for k in range(-max_off, max_off + 1):
        j = i + k
        if k and 0 <= j < len(ref):
            mk = mae(ref[j], mine[i])
            if mk < best * 0.85:   # clearly better than the same-index frame
                best_k, best = k, mk
    rows.append({"frame": i, "ref_frame": ref_start + i, "mae": round(m, 2), "psnr": round(psnr, 2), "ssim": round(ssim(ref[i], mine[i]), 4),
                 "best_offset": best_k})
# reference cuts: a frame-to-frame difference far above the clip's typical motion
d = [mae(ref[i - 1], ref[i]) for i in range(1, n)]
thr = max(25.0, float(np.median(d)) * 4) if d else 1e9
cuts = [i for i in range(1, n) if d[i - 1] > thr]
bounds = sorted({j for c in cuts for j in (c - 1, c, c + 1) if 0 <= j < n})
worst = sorted(rows, key=lambda r: -r["mae"])[:n_worst]
lead = [r for r in rows if r["best_offset"]]
summary = {"frames": n, "mean_mae": round(float(np.mean([r["mae"] for r in rows])), 2), "max_mae": max(r["mae"] for r in rows),
           "mean_ssim": round(float(np.mean([r["ssim"] for r in rows])), 4), "ref_cuts": [ref_start + c for c in cuts],
           "temporal_mismatches": len(lead)}
if baseline:
    import subprocess
    import tempfile
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,bit_rate,pix_fmt",
                                    "-of", "json", sys.argv[2]], capture_output=True, text=True).stdout)["streams"][0]
    enc = {"h264": "libx264", "hevc": "libx265", "vp9": "libvpx-vp9", "prores": "prores_ks", "av1": "libaom-av1"}.get(pr["codec_name"], "libx264")
    ctl = os.path.join(tempfile.mkdtemp(), "control.mp4" if enc != "prores_ks" else "control.mov")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", sys.argv[1], "-c:v", enc, "-pix_fmt", pr.get("pix_fmt", "yuv420p"), "-an"]
    cmd += ["-b:v", pr["bit_rate"]] if pr.get("bit_rate") else []
    subprocess.run(cmd + [ctl], check=True)
    ctrl = frames(ctl, ref_start, count, width)
    floor = [mae(ref[i], ctrl[i]) for i in range(min(n, len(ctrl)))]
    fl = float(np.percentile(floor, 95)) if floor else 0.0
    for r in rows:
        r["codec_level"] = r["mae"] <= fl + 1.0
    summary.update({"codec_floor_p95": round(fl, 2), "frames_above_codec_floor": sum(not r["codec_level"] for r in rows)})
print(json.dumps(summary))
print("worst:", ", ".join(f"f{r['ref_frame']} mae {r['mae']} ssim {r['ssim']}" for r in worst))
print("boundaries:", ", ".join(f"f{rows[j]['ref_frame']} mae {rows[j]['mae']}" for j in bounds) or "none")
print("lead/lag:", ", ".join(f"f{r['ref_frame']} best {r['best_offset']:+d}" for r in lead[:20]) or "none", "..." if len(lead) > 20 else "")
if out:
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "metrics.json"), "w") as f:
        json.dump({"summary": summary, "frames": rows, "boundaries": [rows[j] for j in bounds]}, f, indent=1)
    tiles = []
    for r in worst:
        a, b = ref[r["frame"]], mine[r["frame"]]
        heat = cv2.applyColorMap(cv2.convertScaleAbs(cv2.absdiff(a, b).max(axis=2), alpha=3), cv2.COLORMAP_INFERNO)
        row = np.hstack([a, b, heat]); cv2.putText(row, f"f{r['ref_frame']} mae {r['mae']}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        tiles.append(row)
    if tiles:
        cv2.imwrite(os.path.join(out, "worst.png"), np.vstack(tiles))
