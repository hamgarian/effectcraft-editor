"""Timed captions from a script, from beats, or from speech recognition; written as SRT, VTT and JSX data for
captionTrack() in jsx/helpers.jsx (burned-in captions).

  python captions.py lines SCRIPT.txt [--start 0.5] [--wps 2.6] [--duration S] [--gap 0.15] --out NAME
  python captions.py beats SCRIPT.txt BEATS.json [--every 2] --out NAME       one line per N beats (scripts/audio.py beats)
  python captions.py whisper WHISPER.json --out NAME                         whisper / faster-whisper JSON segments
-> NAME.srt, NAME.vtt, NAME.jsx (var CAPTIONS = [{t0, t1, text}, ...])
SCRIPT.txt: one caption per line. --duration spreads the lines over a narration's length (e.g. from scripts/tts.py).
"""
import json
import sys


def stamp(t, sep=","):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h:02d}:{m:02d}:{t % 60:06.3f}".replace(".", sep)


def write(caps, name):
    with open(name + ".srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(caps, 1):
            f.write(f"{i}\n{stamp(c['t0'])} --> {stamp(c['t1'])}\n{c['text']}\n\n")
    with open(name + ".vtt", "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n" + "".join(f"{stamp(c['t0'], '.')} --> {stamp(c['t1'], '.')}\n{c['text']}\n\n" for c in caps))
    with open(name + ".jsx", "w", encoding="utf-8") as f:
        f.write("var CAPTIONS = " + json.dumps(caps, ensure_ascii=False) + ";\n")
    print(f"{len(caps)} captions -> {name}.srt / .vtt / .jsx")


def from_lines(lines, start=0.5, wps=2.6, duration=None, gap=0.15):
    words = [max(1, len(l.split())) for l in lines]
    if duration:   # spread over a known narration length, proportional to word count
        wps = sum(words) / max(0.1, duration - start - gap * len(lines))
    caps, t = [], start
    for l, n in zip(lines, words):
        d = max(0.8, n / wps)   # never shorter than a readable 0.8 s
        caps.append({"t0": round(t, 3), "t1": round(t + d, 3), "text": l}); t += d + gap
    return caps


def from_beats(lines, beats, every=2):
    b = beats["beats"]; caps = []
    for i, l in enumerate(lines):
        k = i * every
        if k >= len(b):
            break
        caps.append({"t0": b[k], "t1": b[k + every] if k + every < len(b) else b[-1] + 1.0, "text": l})
    return caps


def from_whisper(js):
    segs = js.get("segments", js if isinstance(js, list) else [])
    return [{"t0": round(s["start"], 3), "t1": round(s["end"], 3), "text": s["text"].strip()} for s in segs if s.get("text", "").strip()]


if __name__ == "__main__":
    a = sys.argv[1:]

    def opt(k, d=None, cast=str):
        if k in a:
            i = a.index(k); v = cast(a[i + 1]); del a[i:i + 2]; return v
        return d
    name = opt("--out", "captions")
    if len(a) >= 2 and a[0] == "lines":
        ls = [l.strip() for l in open(a[1], encoding="utf-8") if l.strip()]
        write(from_lines(ls, opt("--start", 0.5, float), opt("--wps", 2.6, float), opt("--duration", None, float), opt("--gap", 0.15, float)), name)
    elif len(a) >= 3 and a[0] == "beats":
        ls = [l.strip() for l in open(a[1], encoding="utf-8") if l.strip()]
        write(from_beats(ls, json.load(open(a[2])), opt("--every", 2, int)), name)
    elif len(a) >= 2 and a[0] == "whisper":
        write(from_whisper(json.load(open(a[1], encoding="utf-8"))), name)
    else:
        sys.exit(__doc__)
