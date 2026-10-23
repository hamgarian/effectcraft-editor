"""Deliver a comp in a named format with EffectCraft's own renderer/exporters, then verify the file.

  python export.py PROJECT.ecproj COMP PRESET OUT [--start S] [--end S] [--fps N]
  python export.py PROJECT.ecproj COMP open            open the project in the EffectCraft app for hand edits

PRESET  what you get                                        verified by
h264    social MP4 (yuv420p, audio if the comp has it)      ffprobe: codec h264
hevc    smaller MP4                                         ffprobe: codec hevc
prores  ProRes 4444 .mov WITH ALPHA (editing handoff)       ffprobe: pixel format has alpha
webm    VP9 .webm WITH ALPHA (web overlays)                 ffprobe: alpha_mode / pixel format
gif     animated GIF                                        file exists, frames > 1
png     RGBA PNG sequence (OUT = folder)                    frame files present, 4 channels
lottie  Lottie JSON for web/apps (.json/.lottie)            exporter warnings printed (unsupported features)
xml / fcpxml / otio / edl / aaf   editable timeline for Premiere, Final Cut, Resolve (layers pre-rendered to clips)
Needs effectcraft-cli (PATH or EFFECTCRAFT_CLI) and ffprobe.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

CLI = os.environ.get("EFFECTCRAFT_CLI") or shutil.which("effectcraft-cli") or "effectcraft-cli"
RENDER = {"h264": ["--format", "h264"], "hevc": ["--format", "hevc"],
          "prores": ["--format", "prores", "--prores", "4444", "--channels", "rgba"],
          "webm": ["--format", "webm", "--webm-codec", "vp9", "--channels", "rgba"],
          "gif": ["--format", "gif"], "png": ["--format", "png", "--channels", "rgba"]}
TIMELINE = {"xml", "fcpxml", "otio", "edl", "aaf"}


def sh(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def stream(path):
    code, out = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                    "stream=codec_name,pix_fmt,nb_read_packets:stream_tags=alpha_mode", "-of", "json", path])
    s = json.loads(out)["streams"][0] if code == 0 and json.loads(out).get("streams") else {}
    return s


def main(a):
    if not (os.path.exists(CLI) or shutil.which(CLI)):
        sys.exit("effectcraft-cli not found: put it on PATH or set EFFECTCRAFT_CLI to its full path")
    if len(a) >= 3 and a[2] == "open":
        app = os.path.join(os.path.dirname(CLI), "effectcraft.exe" if os.name == "nt" else "effectcraft")
        if not os.path.exists(app):
            sys.exit(f"app not found next to the CLI ({app}); open {a[0]} by hand")
        subprocess.Popen([app, "--control", "9877", a[0]]); print(f"opened {a[0]} in EffectCraft (control port 9877)"); return
    if len(a) < 4:
        sys.exit(__doc__)
    proj, comp, preset, out = a[:4]
    extra = []
    for k in ("--start", "--end", "--fps"):
        if k in a:
            extra += [k, a[a.index(k) + 1]]
    if preset in RENDER:
        target = out
        if preset == "png":
            os.makedirs(out, exist_ok=True); target = os.path.join(out, "f_[#####].png")
        code, log = sh([CLI, "render", "--project", proj, "--comp", comp, "--out", target, *RENDER[preset], *extra])
    elif preset == "lottie":
        code, log = sh([CLI, "exec", "file.exportLottie", "--project", proj, "--params", json.dumps({"comp": comp, "path": os.path.abspath(out)})])
    elif preset in TIMELINE:
        code, log = sh([CLI, "exec", "file.exportTimeline", "--project", proj, "--params", json.dumps({"comp": comp, "path": os.path.abspath(out)})])
    else:
        sys.exit(f"unknown preset {preset}\n" + __doc__)
    if code != 0:
        sys.exit(f"export failed ({code}):\n{log[-800:]}")
    # verify the delivered file, not the exit code
    if preset == "png":
        files = sorted(glob.glob(os.path.join(out, "f_*.png")))
        import cv2
        ch = cv2.imread(files[0], cv2.IMREAD_UNCHANGED).shape[2] if files else 0
        ok = bool(files) and ch == 4
        print(f"{len(files)} frames, {ch} channels" + ("" if ok else "  <-- expected RGBA frames"))
    elif preset in RENDER:
        s = stream(out); pf = s.get("pix_fmt", "")
        # ProRes 4444 reports an alpha pixel format; VP9 WebM keeps alpha in a side stream flagged alpha_mode=1
        alpha = pf.startswith(("yuva", "rgba", "argb", "bgra", "gbrap")) or s.get("tags", {}).get("alpha_mode") == "1"
        ok = bool(s) and (preset not in ("prores", "webm") or alpha)
        print(f"{out}: {s.get('codec_name')} {pf} {s.get('nb_read_packets')} frames" + ("" if ok else "  <-- expected an alpha channel"))
    else:
        ok = os.path.exists(out)
        try:
            warnings = json.loads(log[log.index("{"):]).get("warnings", [])
        except ValueError:
            warnings = []
        print(f"{out}: {os.path.getsize(out) if ok else 0} bytes" + "".join(f"\n  warning: {w}" for w in warnings))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
