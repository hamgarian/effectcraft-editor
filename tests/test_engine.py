"""Tests that need a real EffectCraft (skipped without one; set EFFECTCRAFT_CLI). Run: python -m pytest tests -q"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

R = Path(__file__).resolve().parent.parent
CLI = os.environ.get("EFFECTCRAFT_CLI") or shutil.which("effectcraft-cli")
pytestmark = pytest.mark.skipif(not CLI, reason="EffectCraft CLI not found (set EFFECTCRAFT_CLI)")


def build(jsx, cwd):
    subprocess.run([sys.executable, str(R / "scripts" / "bundle.py"), str(jsx), str(cwd / "_b.jsx")], check=True, capture_output=True)
    r = subprocess.run([CLI, "script", "_b.jsx", "--empty"], cwd=cwd, capture_output=True, text=True)
    return r.stdout + r.stderr


@pytest.fixture(scope="module")
def tpl(tmp_path_factory):
    d = tmp_path_factory.mktemp("tpl")
    out = build(R / "tests" / "templates_demo.jsx", d)
    assert "TEMPLATES OK 6" in out, out
    return d


@pytest.mark.parametrize("comp,frame", [("LT", 50), ("TC", 40), ("LR", 30), ("KT", 40), ("OR", 30), ("TC vertical", 40)])
def test_template_renders(tpl, comp, frame):
    png = tpl / f"{comp.replace(' ', '_')}.png"
    subprocess.run([CLI, "render-frame", "--project", "_templates.ecproj", "--comp", comp, "--frame", str(frame), "--out", str(png)],
                   cwd=tpl, capture_output=True)
    img = cv2.imread(str(png))
    assert img is not None and img.std() > 8, f"{comp} rendered blank"


@pytest.mark.parametrize("comp,frame", [("KT", 40), ("LR", 30)])
def test_centred_templates_are_centred(tpl, comp, frame):
    """text parented to a null drifted 50 px up-left (a null's anchor is [50,50]); ink must sit on the frame centre"""
    png = tpl / f"c_{comp}.png"
    subprocess.run([CLI, "render-frame", "--project", "_templates.ecproj", "--comp", comp, "--frame", str(frame), "--out", str(png)],
                   cwd=tpl, capture_output=True)
    g = cv2.cvtColor(cv2.imread(str(png)), cv2.COLOR_BGR2GRAY).astype(int)
    ys, xs = np.where(np.abs(g - np.median(g)) > 60)
    cy, cx = (ys.min() + ys.max()) / 2 / g.shape[0], (xs.min() + xs.max()) / 2 / g.shape[1]
    assert abs(cy - 0.5) < 0.03 and abs(cx - 0.5) < 0.03, (cx, cy)


def test_exported_template_takes_new_values(tpl):
    (tpl / "v.json").write_text(json.dumps({"Name": "ADA LOVELACE", "Role": "first programmer"}))
    for out, extra in (("default.png", []), ("values.png", ["--values", "v.json"])):
        subprocess.run([CLI, "render-frame", "--template", "_lower_third.ectemplate", *extra, "--frame", "50", "--out", out], cwd=tpl, capture_output=True)
    a, b = cv2.imread(str(tpl / "default.png")), cv2.imread(str(tpl / "values.png"))
    assert a is not None and b is not None and np.abs(a.astype(int) - b.astype(int)).mean() > 0.5, "values did not change the render"


@pytest.mark.parametrize("preset,out", [("prores", "lt.mov"), ("webm", "lt.webm"), ("png", "seq"), ("lottie", "lt.json"), ("otio", "lt.otio")])
def test_export_presets_verify(tpl, preset, out):
    r = subprocess.run([sys.executable, str(R / "scripts" / "export.py"), "_templates.ecproj", "LT", preset, out], cwd=tpl,
                       capture_output=True, text=True, env={**os.environ, "EFFECTCRAFT_CLI": CLI})
    assert r.returncode == 0, r.stdout + r.stderr


def test_track_attach_follows_feature(tmp_path):
    vw = cv2.VideoWriter(str(tmp_path / "raw.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 25, (320, 240))
    rng = np.random.default_rng(1); bg = cv2.GaussianBlur(rng.integers(60, 120, (240, 320, 3), dtype=np.uint8), (5, 5), 0)
    for i in range(50):
        f = bg.copy(); x = 60 + i * 4; y = 120 + int(30 * np.sin(i / 8))
        cv2.rectangle(f, (x - 12, y - 12), (x + 12, y + 12), (255, 255, 255), -1); cv2.circle(f, (x, y), 5, (0, 0, 0), -1); vw.write(f)
    vw.release()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp_path / "raw.mp4"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(tmp_path / "dot.mp4")], check=True)
    out = build(R / "tests" / "track_demo.jsx", tmp_path)
    line = next(l for l in out.splitlines() if l.startswith("TRACK"))
    x1, y1 = map(float, line.split()[2].split(","))
    # frame 40 (1.6 s): the square is at x = 60 + 40*4 = 220, y = 120 + 30 sin(5) = 91.2
    assert abs(x1 - 220) < 4 and abs(y1 - 91.2) < 4, line
