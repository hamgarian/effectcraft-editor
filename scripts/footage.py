"""Footage prep and analysis for editing real clips in EffectCraft. Outputs JSON that jsx/footage.jsx reads
(cut lists, colour matches, reframe keys). Needs ffmpeg/ffprobe, numpy, opencv-python.

  python footage.py probe DIR_or_FILES...                 duration, fps (flags VARIABLE frame rate), size, rotation, audio
  python footage.py conform IN OUT [--fps 25] [--size 1920x1080] [--lut x.cube] [--proxy]
                                                          constant frame rate, rotation baked, every frame a keyframe
                                                          (frame-accurate in EffectCraft); --proxy = half size, fast
  python footage.py scenes IN [--thresh 4] [--out shots.json]          shot boundaries -> [{file, in, out}]
  python footage.py silences IN [--db -35] [--min 0.4] [--pad 0.08] [--out keep.json]
                                                          cut list of the parts with sound (talking-head tightening)
  python footage.py beatcut MUSIC CLIP... [--every 1] [--out cuts.json] [--start 0]
                                                          one clip per beat interval, from each clip's busiest stretch
  python footage.py colormatch REF TARGET [--ref-t S] [--target-t S] [--out match.json] [--cube match.cube]
                                                          make TARGET look like REF: per-channel Levels + a 3D LUT
  python footage.py reframe IN [--aspect 9:16] [--every 5] [--out keys.json]
                                                          follow the subject (faces, else motion) for a vertical crop
  python footage.py normalize IN OUT [--lufs -14]         loudness to target (two-pass loudnorm), video copied
Cut lists are [{"file": path, "in": s, "out": s}] in source seconds; jsx assemble() places them back to back.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def probe(path):
    code, out, err = sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    if code != 0:
        return {"file": path, "error": err.strip()[-200:]}
    j = json.loads(out); v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if not v:
        return {"file": path, "error": "no video"}

    def rate(x):
        n, d = map(float, x.split("/")); return n / d if d else 0.0
    r, avg = rate(v.get("r_frame_rate", "0/1")), rate(v.get("avg_frame_rate", "0/1"))
    rot = 0
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", rot))
    rot = int(v.get("tags", {}).get("rotate", rot))
    return {"file": path, "duration": round(float(j["format"].get("duration", 0)), 3), "fps": round(r, 3), "avg_fps": round(avg, 3),
            "vfr": abs(r - avg) > 0.05 * max(r, 1), "size": f"{v['width']}x{v['height']}", "rotation": rot,
            "audio": any(s["codec_type"] == "audio" for s in j["streams"]), "codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
            "profile": v.get("profile"),
            # EffectCraft 0.16 renders H.264 "High 4:4:4 Predictive" (any lossless x264, even 4:2:0) as black frames, no error
            "needs_conform": abs(r - avg) > 0.05 * max(r, 1) or (v.get("codec_name") == "h264" and "4:4:4" in str(v.get("profile", "")))}


def conform(src, dst, fps=25.0, size=None, lut=None, proxy=False):
    vf = [f"fps={fps}"]
    if size:
        w, h = size.split("x"); vf.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    if proxy:
        vf.append("scale=trunc(iw/4)*2:trunc(ih/4)*2")
    if lut:
        vf.append(f"lut3d='{lut.replace(os.sep, '/').replace(':', chr(92) + ':')}'")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast" if proxy else "medium",
           "-crf", "28" if proxy else "16", "-g", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", dst]
    code, _, err = sh(cmd)   # ffmpeg applies the rotation flag before filters (autorotate), so the output is upright
    if code != 0:
        sys.exit(err[-500:])
    print(json.dumps(probe(dst)))


def frame_diffs(path, w=96):
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25; prev = None; d = []; hist = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.resize(f, (w, int(w * f.shape[0] / f.shape[1])))
        h = cv2.calcHist([cv2.cvtColor(g, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256]); cv2.normalize(h, h)
        d.append(0.0 if prev is None else float(np.abs(g.astype(np.int16) - prev[0]).mean()) * (1 + float(cv2.compareHist(prev[1], h, cv2.HISTCMP_BHATTACHARYYA))))
        prev = (g.astype(np.int16), h)
    return np.array(d), fps


def scenes(path, thresh=4.0):
    d, fps = frame_diffs(path)
    if len(d) < 3:
        return [{"file": path, "in": 0.0, "out": round(len(d) / fps, 3)}]
    med = np.array([np.median(d[max(1, i - 12):i + 13]) for i in range(len(d))])   # local motion level
    cuts = [i for i in range(1, len(d)) if d[i] > max(12.0, thresh * med[i]) and d[i] >= d[i - 1] and (i + 1 >= len(d) or d[i] >= d[i + 1])]
    edges = [0] + cuts + [len(d)]
    return [{"file": path, "in": round(edges[k] / fps, 3), "out": round(edges[k + 1] / fps, 3)} for k in range(len(edges) - 1)]


def silences(path, db=-35.0, min_len=0.4, pad=0.08):
    _, _, err = sh(["ffmpeg", "-v", "info", "-i", path, "-af", f"silencedetect=noise={db}dB:d={min_len}", "-f", "null", "-"])
    dur = probe(path)["duration"]; quiet = []; start = None
    for line in err.splitlines():
        if "silence_start:" in line:
            start = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and start is not None:
            quiet.append((max(0.0, start), float(line.split("silence_end:")[1].split()[0]))); start = None
    if start is not None:
        quiet.append((start, dur))
    keep, t = [], 0.0
    for a, b in quiet:
        if a - t > 0.05:
            keep.append({"file": path, "in": round(max(0.0, t - pad if t else 0.0), 3), "out": round(min(dur, a + pad), 3)})
        t = b
    if dur - t > 0.05:
        keep.append({"file": path, "in": round(max(0.0, t - pad), 3), "out": round(dur, 3)})
    return keep, quiet


def busiest(path, length):
    """start time of the window with the most motion (an action beat beats a static one)"""
    d, fps = frame_diffs(path, 64)
    n = max(1, int(round(length * fps)))
    if len(d) <= n:
        return 0.0
    s = np.convolve(d, np.ones(n), mode="valid")
    return round(float(np.argmax(s)) / fps, 3)


def beatcut(music, clips, every=1, start=0.0):
    import audio
    _, bt, _ = audio.beats(audio.decode(music), audio.SR)
    bt = [b for b in bt if b >= start][::every]
    out = []
    for k in range(len(bt) - 1):
        clip = clips[k % len(clips)]; length = bt[k + 1] - bt[k]
        dur = probe(clip)["duration"]
        if dur < length:
            continue
        s = min(busiest(clip, length), dur - length)
        out.append({"file": clip, "in": s, "out": round(s + length, 3), "at": round(bt[k], 3)})
    return out


def frame_at(path, t):
    if path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
        return cv2.imread(path)
    cap = cv2.VideoCapture(path); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read()
    if not ok:
        sys.exit(f"could not read {path} at {t}s")
    return f


def colormatch(ref, tgt):
    """per-channel Levels (percentile mapping, for EffectCraft's Levels (Individual Controls)) + a Reinhard Lab
    transfer baked into a 33-point 3D LUT (for ffmpeg lut3d / conform --lut)"""
    lv = {}
    for ch, name in zip(range(3), ("Blue", "Green", "Red")):
        r1, r50, r99 = np.percentile(ref[:, :, ch], [1, 50, 99]); t1, t50, t99 = np.percentile(tgt[:, :, ch], [1, 50, 99])
        ib, iw = t1 / 255, max(t99, t1 + 1) / 255; ob, ow = r1 / 255, max(r99, r1 + 1) / 255
        mid_t = np.clip((t50 / 255 - ib) / (iw - ib), 1e-3, 1 - 1e-3); mid_r = np.clip((r50 / 255 - ob) / (ow - ob), 1e-3, 1 - 1e-3)
        gamma = float(np.clip(np.log(mid_t) / np.log(mid_r), 0.2, 5.0))   # Levels: out = in^(1/gamma)
        lv[name] = {"Input Black": round(float(ib), 4), "Input White": round(float(iw), 4), "Gamma": round(gamma, 4),
                    "Output Black": round(float(ob), 4), "Output White": round(float(ow), 4)}
    rl, tl = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64), cv2.cvtColor(tgt, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
    rm, rs, tm, ts = rl.mean(0), rl.std(0) + 1e-6, tl.mean(0), tl.std(0) + 1e-6
    n = 33; g = np.linspace(0, 255, n)
    b_, g_, r_ = np.meshgrid(g, g, g, indexing="ij")
    cube_bgr = np.stack([b_, g_, r_], -1).reshape(-1, 1, 3).astype(np.uint8)
    lab = cv2.cvtColor(cube_bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
    lab = (lab - tm) / ts * rs + rm
    mapped = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2BGR).reshape(n, n, n, 3) / 255.0
    lines = ["TITLE \"colormatch\"", f"LUT_3D_SIZE {n}"]
    for bi in range(n):          # .cube order: red fastest, then green, then blue
        for gi in range(n):
            for ri in range(n):
                bb, gg, rr = mapped[bi, gi, ri]
                lines.append(f"{rr:.6f} {gg:.6f} {bb:.6f}")
    return lv, "\n".join(lines) + "\n"


def apply_levels(img, lv):
    out = np.empty_like(img, dtype=np.float64)
    for ch, name in zip(range(3), ("Blue", "Green", "Red")):
        p = lv[name]; x = np.clip((img[:, :, ch] / 255 - p["Input Black"]) / (p["Input White"] - p["Input Black"]), 0, 1)
        out[:, :, ch] = (x ** (1 / p["Gamma"])) * (p["Output White"] - p["Output Black"]) + p["Output Black"]
    return np.clip(out * 255, 0, 255).astype(np.uint8)


def reframe(path, aspect="9:16", every=5):
    aw, ah = map(float, aspect.split(":"))
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cw = min(W, H * aw / ah)
    face = None   # some OpenCV builds ship without the face detector: then follow motion only
    if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
        face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs, prev, i = [], None, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); x = None
        if i % every == 0:
            fs = face.detectMultiScale(cv2.resize(g, (W // 2, H // 2)), 1.1, 5, minSize=(24, 24)) if face is not None else []
            if len(fs):
                fx, _, fw, _ = max(fs, key=lambda r: r[2] * r[3]); x = (fx + fw / 2) * 2
            elif prev is not None:   # no face: centre of motion
                m = cv2.absdiff(g, prev); m = cv2.GaussianBlur(m, (21, 21), 0)
                col = m.sum(axis=0).astype(np.float64)
                if col.sum() > 1e3:
                    x = float((col * np.arange(W)).sum() / col.sum())
            xs.append((i, x))
        prev = g; i += 1
    known = [(k, x) for k, x in xs if x is not None]
    if not known:
        known = [(0, W / 2)]
    ks, vs = np.array([k for k, _ in known]), np.array([x for _, x in known])
    allx = np.interp(np.arange(i), ks, vs)
    sm = np.convolve(np.pad(allx, (12, 12), mode="edge"), np.ones(25) / 25, mode="valid")   # 1 s smoothing: a calm operator
    sm = np.clip(sm, cw / 2, W - cw / 2)
    keys = [[round(k / fps, 3), round(float(sm[k]), 1)] for k in range(0, i, every)]
    return {"source": [W, H], "crop": [round(cw, 1), H], "aspect": aspect, "fps": fps, "center_x": keys}


def normalize(src, dst, lufs=-14.0):
    _, _, err = sh(["ffmpeg", "-v", "info", "-i", src, "-af", f"loudnorm=I={lufs}:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"])
    m = json.loads(err[err.rfind("{"):err.rfind("}") + 1])
    af = (f"loudnorm=I={lufs}:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    code, _, err2 = sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:v", "copy", "-af", af, "-ar", "48000", dst])
    if code != 0:
        sys.exit(err2[-400:])
    print(f"{dst}: {m['input_i']} -> {lufs} LUFS")


if __name__ == "__main__":
    a = sys.argv[1:]

    def opt(k, d=None, cast=str):
        if k in a:
            i = a.index(k); v = cast(a[i + 1]); del a[i:i + 2]; return v
        return d

    def flag(k):
        if k in a:
            a.remove(k); return True
        return False
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0); out = opt("--out")
    def emit(obj):
        if out:
            json.dump(obj, open(out, "w"), indent=1); print(out)
        else:
            print(json.dumps(obj, indent=1))
    if cmd == "probe":
        files = [os.path.join(p, f) for p in a for f in sorted(os.listdir(p))] if a and os.path.isdir(a[0]) else a
        for p in files:
            r = probe(p)
            why = "VARIABLE frame rate" if r.get("vfr") else "H.264 High 4:4:4 profile (renders black in EffectCraft)" if r.get("needs_conform") else ""
            print(json.dumps(r) + (f"   <-- {why}: conform it first" if why else ""))
    elif cmd == "conform":
        conform(a[0], a[1], opt("--fps", 25.0, float), opt("--size"), opt("--lut"), flag("--proxy"))
    elif cmd == "scenes":
        emit(scenes(a[0], opt("--thresh", 4.0, float)))
    elif cmd == "silences":
        keep, quiet = silences(a[0], opt("--db", -35.0, float), opt("--min", 0.4, float), opt("--pad", 0.08, float))
        print(f"{len(quiet)} silences removed, {len(keep)} ranges kept, {sum(k['out'] - k['in'] for k in keep):.2f}s of {probe(a[0])['duration']}s",
              file=sys.stderr)
        emit(keep)
    elif cmd == "beatcut":
        emit(beatcut(a[0], a[1:], opt("--every", 1, int), opt("--start", 0.0, float)))
    elif cmd == "colormatch":
        rt, tt, cube = opt("--ref-t", 0.0, float), opt("--target-t", 0.0, float), opt("--cube")
        lv, cube_txt = colormatch(frame_at(a[0], rt), frame_at(a[1], tt))
        if cube:
            open(cube, "w").write(cube_txt); print(cube, file=sys.stderr)
        emit({"levels": lv, "cube": cube})
    elif cmd == "reframe":
        emit(reframe(a[0], opt("--aspect", "9:16"), opt("--every", 5, int)))
    elif cmd == "normalize":
        normalize(a[0], a[1], opt("--lufs", -14.0, float))
    else:
        sys.exit(__doc__)
