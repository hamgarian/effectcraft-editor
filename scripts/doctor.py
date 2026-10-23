"""Check this machine can run the skill, print what is missing and how to fix it. Any OS.
Usage: python doctor.py
"""
import importlib
import os
import platform
import shutil
import subprocess
import sys


def ver(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "ok"
    except (OSError, subprocess.TimeoutExpired) as e:
        return None if isinstance(e, OSError) else "timed out"


def find_blender():
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    w = shutil.which("blender")
    if w:
        return w
    for pat in ("C:/Program Files/Blender Foundation/Blender */blender.exe", "/Applications/Blender.app/Contents/MacOS/Blender"):
        import glob
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


rows, bad = [], 0
def row(name, ok, detail, fix=""):
    global bad
    bad += 0 if ok or ok is None else 1
    rows.append((("OK  " if ok else "--  " if ok is None else "MISS") + f" {name:16} {detail}" + (f"\n      fix: {fix}" if fix and not ok else "")))


row("python", sys.version_info >= (3, 10), platform.python_version(), "install Python 3.10+")
for mod, pip in (("cv2", "opencv-python"), ("numpy", "numpy"), ("PIL", "pillow"), ("pytest", "pytest")):
    try:
        importlib.import_module(mod); row(mod, True, "importable")
    except ImportError:
        row(mod, False, "missing", f"pip install {pip}")
for tool in ("ffmpeg", "ffprobe"):
    v = ver([tool, "-version"])
    row(tool, v is not None, v or "not on PATH", "install ffmpeg (ffmpeg.org; brew install ffmpeg; apt install ffmpeg) and put it on PATH")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ec_cli import find_cli  # noqa: E402

cli = find_cli()   # EFFECTCRAFT_CLI, PATH, usual install folders, unpacked zips in Downloads/Desktop/Documents
v = ver([cli, "info"]) if cli else None
saved = os.environ.get("EFFECTCRAFT_CLI")
row("effectcraft-cli", v is not None, (cli + " -> " + v + ("" if saved else "  (found by search: save it with ec_cli.py --set)")) if v else "not found",
    "ask the user where EffectCraft is (the folder with effectcraft-cli), or install it from "
    "github.com/storytold/effectcraft/releases; then: python scripts/ec_cli.py --set <path>")
b = find_blender()
row("blender", (b is not None) or None, b or "not found (optional: photoreal 3D sets)", "install Blender 4.2+ or set BLENDER=path")
for opt_tool, why in (("piper", "local TTS (optional)"), ("whisper", "caption timing from speech (optional)")):
    row(opt_tool, (shutil.which(opt_tool) is not None) or None, shutil.which(opt_tool) or f"not found ({why})")
print("\n".join(rows))
if cli:
    print(f"\nMCP (optional): claude mcp add --scope user effectcraft -- \"{cli}\" mcp --autosave")
print(f"\n{'ready' if bad == 0 else f'{bad} required item(s) missing'}")
sys.exit(1 if bad else 0)
