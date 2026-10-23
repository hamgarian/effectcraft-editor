"""Audio for edits: find the beat, make sound effects, mix and mux, check cuts land on beats, compare audio to a reference.
Needs ffmpeg/ffprobe on PATH and numpy. No audio libraries.

  python audio.py beats MUSIC [--fps 20] [--out beats.json]      tempo, beat times, hits (strong onsets), as seconds and frames
  python audio.py sfx OUT_DIR                                     original whoosh / click / impact / riser / pop / swish WAVs
  python audio.py mix --cues cues.json --out mix.wav [--music M] [--music-gain -3] [--duration S]
  python audio.py mux VIDEO AUDIO OUT.mp4                         put audio under a (silent) render, video stream copied
  python audio.py cutsync VIDEO MUSIC [--tol 1]                   each video cut vs the nearest beat/hit, in frames
  python audio.py check REF MINE                                  loudness, peak, duration, and sync lag between the two tracks

cues.json: [{"t": 0.95, "sfx": "whoosh.wav", "gain": -6}, ...]  (paths relative to the cues file)
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100


def decode(path, sr=SR, mono=True):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1" if mono else "2", "-ar", str(sr), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg could not decode audio from {path}: {r.stderr.decode()[-300:]}")
    a = np.frombuffer(r.stdout, np.float32)
    return a if mono else a.reshape(-1, 2)


def write_wav(path, a, sr=SR):
    a = np.atleast_2d(a.T).T if a.ndim == 1 else a
    pcm = (np.clip(a, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(pcm.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def onset_env(a, sr, hop=512, n=2048):
    """spectral flux: how much new energy arrives per hop (positive spectrum differences, log-compressed)"""
    if len(a) < n:
        a = np.pad(a, (0, n - len(a)))
    frames = np.lib.stride_tricks.sliding_window_view(a, n)[::hop] * np.hanning(n)
    mag = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(np.diff(mag, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")   # remove slow loudness swells
    flux = np.maximum(flux, 0)
    return flux / (flux.max() or 1), sr / hop


def beats(a, sr):
    env, rate = onset_env(a, sr)
    lags = np.arange(int(rate * 60 / 200), int(rate * 60 / 60) + 1)            # 200..60 BPM
    ac = np.array([np.dot(env[:-l], env[l:]) for l in lags])
    bpm_of = 60 * rate / lags
    ac *= np.exp(-0.5 * (np.log2(bpm_of / 120) / 1.0) ** 2)                     # mild prior toward 120 BPM
    period = lags[int(np.argmax(ac))]
    phase = int(np.argmax([env[p::period].sum() for p in range(period)]))
    bt = []
    for b in range(phase, len(env), period):                                     # snap each grid beat to the nearest peak
        lo, hi = max(0, b - period // 8), min(len(env), b + period // 8 + 1)
        bt.append((lo + int(np.argmax(env[lo:hi]))) / rate)
    thr = env.mean() + 1.5 * env.std()
    hits, last = [], -1.0
    for i in range(1, len(env) - 1):
        if env[i] > thr and env[i] >= env[i - 1] and env[i] >= env[i + 1] and i / rate - last > 0.1:
            hits.append(i / rate); last = i / rate
    return 60 * rate / period, bt, hits


def tone(f0, f1, dur, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur)))


def env_ad(n, attack, sr=SR):
    a = int(attack * sr); e = np.ones(n)
    e[:a] = np.linspace(0, 1, a) if a else 1
    e[a:] = np.exp(-np.linspace(0, 6, n - a))
    return e


def sfx_bank(out):
    """original synthesized effects (no licences involved)"""
    rng = np.random.default_rng(7)
    os.makedirs(out, exist_ok=True)

    def noise(dur):
        return rng.standard_normal(int(dur * SR))

    def lowpass(x, k):
        return np.convolve(x, np.ones(k) / k, mode="same")
    n = int(0.45 * SR); t = np.linspace(0, 1, n)
    whoosh = sum(lowpass(noise(0.45), k) * w for k, w in [(40, 1.0), (12, 0.6), (4, 0.3)]) * np.sin(np.pi * t) ** 2
    swish = lowpass(noise(0.18), 6) * np.sin(np.pi * np.linspace(0, 1, int(0.18 * SR))) ** 3
    click = (noise(0.03) * 0.6 + tone(2400, 1800, 0.03)) * env_ad(int(0.03 * SR), 0.001)
    impact = (tone(90, 38, 0.6) + lowpass(noise(0.6), 30) * 0.5) * env_ad(int(0.6 * SR), 0.002)
    riser = (tone(200, 1200, 1.2) * 0.5 + lowpass(noise(1.2), 8) * 0.5) * np.linspace(0, 1, int(1.2 * SR)) ** 2
    pop = tone(500, 1400, 0.08) * env_ad(int(0.08 * SR), 0.002)
    for name, a in [("whoosh", whoosh), ("swish", swish), ("click", click), ("impact", impact), ("riser", riser), ("pop", pop)]:
        write_wav(os.path.join(out, name + ".wav"), 0.9 * a / (np.abs(a).max() or 1))
        print(os.path.join(out, name + ".wav"))


def mix(cues_path, out, music=None, music_gain=-3.0, duration=None):
    cues = json.load(open(cues_path)) if cues_path else []
    base = os.path.dirname(os.path.abspath(cues_path)) if cues_path else "."
    mus = decode(music, mono=False) * 10 ** (music_gain / 20) if music else np.zeros((0, 2), np.float32)
    end = max([len(mus) / SR] + [c["t"] + 2 for c in cues]) if duration is None else duration
    bus = np.zeros((int(end * SR), 2), np.float32)
    bus[:min(len(mus), len(bus))] += mus[:len(bus)]
    for c in cues:
        s = decode(os.path.join(base, c["sfx"]), mono=False) * 10 ** (c.get("gain", -6) / 20)
        i = int(c["t"] * SR); j = min(len(bus), i + len(s))
        if i < len(bus):
            bus[i:j] += s[:j - i]
    peak = np.abs(bus).max()
    if peak > 0.89:   # leave headroom: -1 dBFS
        bus *= 0.89 / peak
    write_wav(out, bus)
    print(f"{out}: {end:.2f}s, {len(cues)} cues, peak {20 * np.log10(max(np.abs(bus).max(), 1e-9)):.1f} dBFS")


def mux(video, audio, out):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-400:])
    print(out)


def video_cuts(path):
    import cv2
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 25; prev = None; d = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (96, 54)).astype(np.int16)
        d.append(0 if prev is None else float(np.abs(g - prev).mean())); prev = g
    d = np.array(d); thr = max(25.0, float(np.median(d[1:])) * 4) if len(d) > 2 else 1e9
    return [i for i in range(1, len(d)) if d[i] > thr], fps


def cutsync(video, music, tol=1):
    cuts, fps = video_cuts(video)
    _, bt, hits = beats(decode(music), SR)
    marks = np.array(sorted(bt + hits)) if bt or hits else np.array([0.0])
    ok = 0
    for c in cuts:
        off = (marks[np.argmin(np.abs(marks - c / fps))] - c / fps) * fps
        ok += abs(off) <= tol
        print(f"cut f{c} {c / fps:.2f}s  nearest beat/hit {off:+.1f} f" + ("" if abs(off) <= tol else "  <-- off beat"))
    print(f"{ok}/{len(cuts)} cuts within {tol} frame(s) of a beat or hit")


def lufs(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr
    def grab(key):
        i = txt.rfind(key)
        return float(txt[i:].split(":")[1].split()[0]) if i >= 0 else float("nan")
    return grab("I:"), grab("Peak:")


def check(ref, mine):
    for name, p in (("ref", ref), ("mine", mine)):
        has = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                             capture_output=True, text=True).stdout.strip()
        if not has:
            print(f"{name}: NO AUDIO STREAM"); return
        i, pk = lufs(p)
        print(f"{name}: {len(decode(p, 8000)) / 8000:.2f}s  loudness {i:.1f} LUFS  true peak {pk:.1f} dBTP")
    ea, rate = onset_env(decode(ref, 11025), 11025, hop=256, n=1024)
    eb, _ = onset_env(decode(mine, 11025), 11025, hop=256, n=1024)
    n = min(len(ea), len(eb)); m = int(rate * 1.0)
    lags = range(-m, m + 1)
    sc = [np.dot(ea[max(0, l):n + min(0, l)], eb[max(0, -l):n - max(0, l)]) for l in lags]
    sc = np.array(sc); near_best = [l for l, s in zip(lags, sc) if s >= 0.95 * sc.max()]
    lag = min(near_best, key=abs) / rate   # periodic music matches at every beat: take the smallest shift that fits
    print(f"sync: mine is {'late' if lag < 0 else 'early'} by {abs(lag) * 1000:.0f} ms" if abs(lag) > 0.02 else "sync: aligned within 20 ms")


if __name__ == "__main__":
    a = sys.argv[1:]

    def opt(k, d=None, cast=str):
        if k in a:
            i = a.index(k); v = cast(a[i + 1]); del a[i:i + 2]; return v
        return d
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    if cmd == "beats":
        fps, out = opt("--fps", 20.0, float), opt("--out")
        bpm, bt, hits = beats(decode(a[0]), SR)
        res = {"bpm": round(bpm, 1), "beats": [round(b, 3) for b in bt], "hits": [round(h, 3) for h in hits],
               "beat_frames": [int(round(b * fps)) for b in bt], "hit_frames": [int(round(h * fps)) for h in hits], "fps": fps}
        print(f"tempo {res['bpm']} BPM, {len(bt)} beats, {len(hits)} hits")
        if out:
            json.dump(res, open(out, "w"), indent=1); print(out)
        else:
            print(json.dumps(res))
    elif cmd == "sfx":
        sfx_bank(a[0])
    elif cmd == "mix":
        mix(opt("--cues"), opt("--out", "mix.wav"), opt("--music"), opt("--music-gain", -3.0, float), opt("--duration", None, float))
    elif cmd == "mux":
        mux(*a[:3])
    elif cmd == "cutsync":
        tol = opt("--tol", 1.0, float); cutsync(a[0], a[1], tol)
    elif cmd == "check":
        check(a[0], a[1])
    else:
        sys.exit(__doc__)
