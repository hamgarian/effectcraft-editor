"""Lock the timebase: reference vs candidate stream facts side by side, mismatches flagged; optional SHA-256 of
delivered copies (proves the archive copy is the file you checked).
Usage: python probe.py REF.mp4 MINE.mp4 [--sha FILE ...]
Needs ffprobe (ships with ffmpeg) on PATH.
"""
import hashlib
import json
import subprocess
import sys


def facts(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffprobe failed on {path}: {r.stderr.strip()}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        sys.exit(f"{path}: no video stream")
    num, den = map(int, v.get("r_frame_rate", "0/1").split("/"))
    return {
        "size": f"{v['width']}x{v['height']}",
        "fps": round(num / den, 3) if den else 0,
        "frames": int(v.get("nb_read_frames") or v.get("nb_frames") or 0),
        # the video stream's duration: the container's includes audio padding (a 20.0 s render vs 20.032 s reference)
        "duration": round(float(v.get("duration") or j["format"].get("duration", 0)), 3),
        "start": round(float(v.get("start_time", 0) or 0), 3),
        "pix_fmt": v.get("pix_fmt", "?"),
        "audio": any(s["codec_type"] == "audio" for s in j["streams"]),
    }


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


args = sys.argv[1:]
shas = []
if "--sha" in args:
    i = args.index("--sha"); shas = args[i + 1:]; args = args[:i]
if len(args) != 2:
    sys.exit(__doc__)
ref, mine = facts(args[0]), facts(args[1])
bad = 0
print(f"{'':10}{'REF':>16}{'MINE':>16}")
for k in ref:
    flag = ""
    if ref[k] != mine[k] and k != "audio":   # renders are usually silent; audio is informational
        flag = "  <-- differs"; bad += 1
    print(f"{k:10}{str(ref[k]):>16}{str(mine[k]):>16}{flag}")
print(f"timebase: {'LOCKED' if bad == 0 else f'{bad} mismatch(es)'}")
for p in shas:
    print(f"sha256 {sha256(p)}  {p}")
