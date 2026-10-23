"""Render a comp one frame per process (batch render runs out of memory on long comps in 0.14), resumable, then encode.
Any OS; replaces render_seq.ps1. Frames that already exist are kept unless --force; failed frames are retried.

  python render_seq.py PROJECT.ecproj COMP FRAMES OUT.mp4 [--fps 20] [--seq DIR] [--from N] [--to N] [--force] [--retries 2]
Writes DIR/f_00000.png ...; records the run in ledger.jsonl (scripts/ledger.py). Needs effectcraft-cli and ffmpeg.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ec_cli import find_cli  # noqa: E402
from ledger import Ledger  # noqa: E402

a = sys.argv[1:]


def opt(k, d, cast=str):
    if k in a:
        i = a.index(k); v = cast(a[i + 1]); del a[i:i + 2]; return v
    return d


fps, seq, f0, f1 = opt("--fps", 20, int), opt("--seq", None), opt("--from", 0, int), opt("--to", None, int)
retries, force = opt("--retries", 2, int), "--force" in a
a = [x for x in a if x != "--force"]
if len(a) != 4:
    sys.exit(__doc__)
proj, comp, frames, out = a[0], a[1], int(a[2]), a[3]
cli = find_cli()
if not cli:
    sys.exit("effectcraft-cli not found: ask the user where EffectCraft is, then `python scripts/ec_cli.py --set PATH`")
seq = seq or f"seq_{comp}".replace(" ", "_")
os.makedirs(seq, exist_ok=True)
f1 = frames - 1 if f1 is None else f1
with Ledger().step(f"render {comp}", inputs=[proj]) as step:
    todo = [n for n in range(f0, f1 + 1) if force or not os.path.exists(os.path.join(seq, f"f_{n:05d}.png"))]
    print(f"{len(todo)} of {f1 - f0 + 1} frames to render ({f1 - f0 + 1 - len(todo)} already done)")
    failed = []
    for k, n in enumerate(todo):
        p = os.path.join(seq, f"f_{n:05d}.png")
        for _ in range(retries + 1):
            subprocess.run([cli, "render-frame", "--project", proj, "--comp", comp, "--frame", str(n), "--out", p], capture_output=True)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                break
        else:
            failed.append(n)
        if k % 25 == 0:
            print(f"  {k + 1}/{len(todo)}", flush=True)
    if failed:
        print("FAILED frames:", failed)
        raise SystemExit(f"{len(failed)} frames failed; rerun the same command to resume")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(seq, "f_%05d.png"),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-400:])
    step.outputs += [out]
    print(out)
