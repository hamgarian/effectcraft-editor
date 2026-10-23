"""Tests for the measurement scripts on synthetic videos. Run: python -m pytest tests -q"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

S = Path(__file__).resolve().parent.parent / "scripts"
FPS = 25  # not 20, to prove nothing assumes 20 fps


def run(*args):
    r = subprocess.run([sys.executable, str(S / args[0]), *map(str, args[1:])], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def texture(seed=1, size=600):
    rng = np.random.default_rng(seed)
    img = cv2.resize(rng.integers(0, 255, (60, 60, 3), dtype=np.uint8), (size, size), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(img, (3, 3), 0)


def write(path, frames):
    h, w = frames[0].shape[:2]
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (w, h))
    for f in frames:
        vw.write(f)
    vw.release()


def zoom_frames(n, total_zoom, base):
    out = []
    for i in range(n):
        s = total_zoom ** (i / (n - 1))
        M = cv2.getRotationMatrix2D((300, 300), 0, s)
        out.append(cv2.warpAffine(base, M, (600, 600), borderMode=cv2.BORDER_REFLECT)[150:450, 150:450])
    return out


@pytest.fixture
def vids(tmp_path):
    base = texture()
    ref = zoom_frames(25, 1.3, base) + [np.full((300, 300, 3), 200, np.uint8)] * 25  # push-in, cut at f25, flat grey
    mine = zoom_frames(25, 1.0, base) + [np.full((300, 300, 3), 60, np.uint8)] * 25  # no camera move, too dark
    write(tmp_path / "ref.mp4", ref)
    write(tmp_path / "mine.mp4", mine)
    (tmp_path / "shots.json").write_text(json.dumps([["push", 0.0, 0.96]]))
    return tmp_path


def test_camtrack_reads_zoom_and_fps(vids):
    out = run("camtrack.py", vids / "ref.mp4", vids / "mine.mp4", vids / "shots.json")
    row = next(l for l in out.splitlines() if l.startswith("push"))
    zo = float(row.split("|")[1].split("x")[0])
    zm = float(row.split("|")[2].split("x")[0])
    assert 1.2 < zo < 1.4, row
    assert 0.97 < zm < 1.03, row


def test_camtrack_requires_shots(vids):
    r = subprocess.run([sys.executable, str(S / "camtrack.py"), vids / "ref.mp4", vids / "mine.mp4"], capture_output=True, text=True)
    assert r.returncode != 0


def test_framecmp_finds_cut_and_exposure(vids):
    out = run("framecmp.py", vids / "ref.mp4", vids / "mine.mp4")
    assert "25 (" in out and "1.00s" in out  # cut at frame 25 = 1.00 s at 25 fps
    assert "<-- exposure" in out


def test_glitchfind_flags_single_frame(tmp_path):
    for i in range(10):
        v = 255 if i == 5 else 100
        cv2.imwrite(str(tmp_path / f"f_{i:05d}.png"), np.full((50, 50, 3), v, np.uint8))
    out = run("glitchfind.py", tmp_path, "--fps=25")
    assert "f005" in out and "0.20s" in out
    assert "total flagged: 1" in out


def test_edgeblack_flags_exposed_border(tmp_path):
    for i in range(4):
        img = np.full((200, 200, 3), 150, np.uint8)
        if i == 2:
            img[:, :40] = 0
        cv2.imwrite(str(tmp_path / f"f_{i:05d}.png"), img)
    out = run("edgeblack.py", tmp_path)
    assert "): 1" in out and "f002" in out


def test_framestudy_letterbox_and_pick(tmp_path):
    frames = []
    for _ in range(5):
        f = np.full((200, 160, 3), (30, 20, 10), np.uint8)  # BGR -> #0a141e
        f[:12] = 0
        f[-12:] = 0
        frames.append(f)
    write(tmp_path / "lb.mp4", frames)
    out = run("framestudy.py", tmp_path / "lb.mp4", tmp_path / "s.png", 0, 4, "--pick", "80,100")
    assert "top 12px, bottom 12px" in out or "top 11px" in out or "top 13px" in out, out
    assert (tmp_path / "s.png").exists()


def test_bundle_inlines_and_detects_cycle(tmp_path):
    (tmp_path / "a.jsx").write_text('#include "b.jsx"\nvar a = 1;\n')
    (tmp_path / "b.jsx").write_text("var b = 2;\n")
    run("bundle.py", tmp_path / "a.jsx", tmp_path / "out.jsx")
    assert (tmp_path / "out.jsx").read_text() == "var b = 2;\n\nvar a = 1;\n"
    (tmp_path / "b.jsx").write_text('#include "a.jsx"\n')
    r = subprocess.run([sys.executable, str(S / "bundle.py"), tmp_path / "a.jsx", tmp_path / "o2.jsx"], capture_output=True, text=True)
    assert "include cycle" in (r.stdout + r.stderr)


def test_bracecheck_flags_comment_eating_braces(tmp_path):
    (tmp_path / "bad.jsx").write_text("function f() { if (x) { y(); // note } }\nvar z = 1;\n")
    out = run("bracecheck.py", tmp_path / "bad.jsx")
    assert "depth 2 at a top-level statement" in out
    (tmp_path / "ok.jsx").write_text("function f() { if (x) { y(); } }\nvar z = 1;\n")
    assert "end depth 0" in run("bracecheck.py", tmp_path / "ok.jsx")
