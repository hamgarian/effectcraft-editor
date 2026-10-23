"""Tests that need a real EffectCraft (skipped without one; set EFFECTCRAFT_CLI). Run: python -m pytest tests -q"""
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "scripts"))
from ec_cli import find_cli  # noqa: E402

CLI = find_cli()
pytestmark = pytest.mark.skipif(not CLI, reason="EffectCraft CLI not found (python scripts/ec_cli.py --set PATH)")


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


@pytest.fixture(scope="module")
def foot(tmp_path_factory):
    d = tmp_path_factory.mktemp("foot")
    for name, col in (("red", "red"), ("green", "lime"), ("blue", "blue")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={col}:size=320x240:rate=25:duration=2",
                        "-c:v", "libx264", "-crf", "1", "-pix_fmt", "yuv420p", str(d / f"{name}.mp4")], check=True)   # 4:4:4 H.264 renders black in 0.16
    vw = cv2.VideoWriter(str(d / "ramp_raw.avi"), cv2.VideoWriter_fourcc(*"MJPG"), 25, (320, 240))
    for i in range(100):   # grey level = 2 x frame number: a rendered pixel tells which source frame is showing
        vw.write(np.full((240, 320, 3), 2 * i, np.uint8))
    vw.release()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "ramp_raw.avi"), "-c:v", "libx264", "-crf", "1", "-pix_fmt", "yuv420p",
                    str(d / "ramp.mp4")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:size=320x240:rate=25:duration=4", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    str(d / "tone.mp4")], check=True)
    out = build(R / "tests" / "footage_demo.jsx", d)
    line = next((l for l in out.splitlines() if l.startswith("FOOT ")), None)
    assert line, out
    return d, json.loads(line[5:])


def px(d, comp, t, xy=(160, 120)):
    png = d / f"{comp}_{t}.png"
    subprocess.run([CLI, "render-frame", "--project", "_footage.ecproj", "--comp", comp, "--time", str(t), "--out", str(png)], cwd=d, capture_output=True)
    img = cv2.imread(str(png)); assert img is not None, f"{comp} at {t}s did not render"
    return img[xy[1], xy[0]].astype(int)   # BGR


def src_frame(d, comp, t):
    return px(d, comp, t)[1] / 2.0   # grey = 2 x source frame


def test_assemble_cuts_and_crossfade(foot):
    d, _ = foot
    assert px(d, "ASM", 0.5)[2] > 200 and px(d, "ASM", 0.5)[1] < 60       # red
    assert px(d, "ASM", 1.3)[1] > 200 and px(d, "ASM", 1.3)[2] < 60       # green
    mid = px(d, "ASM", 1.8); assert 60 < mid[0] < 200 and 60 < mid[1] < 200   # blue fading in over green
    assert px(d, "ASM", 2.2)[0] > 200                                      # blue


@pytest.mark.parametrize("comp,t,frame", [("RAMP", 0.5, 12.5), ("RAMP", 1.5, 50), ("RAMP", 2.4, 80),   # 1x, then 2x, then 0.5x
                                          ("FREEZE", 1.5, 25), ("FREEZE", 2.5, 37.5),                  # held, then carries on
                                          ("REV", 0.2, 44), ("SPEED", 0.5, 25), ("SLIP", 0.2, 30)])
def test_time_helpers_show_the_right_source_frame(foot, comp, t, frame):
    d, _ = foot
    assert abs(src_frame(d, comp, t) - frame) <= 2, (comp, t, src_frame(d, comp, t), frame)


def test_speed_halves_duration(foot):
    assert abs(foot[1]["speedOut"] - 1.0) < 0.05


def test_pip_and_split_regions(foot):
    d, _ = foot
    assert px(d, "PIP", 0.5, (250, 60))[1] > 200 and px(d, "PIP", 0.5, (50, 200))[2] > 200
    assert px(d, "SPLIT", 0.5, (60, 120))[2] > 200 and px(d, "SPLIT", 0.5, (260, 120))[0] > 200


def test_look_letterbox_and_match(foot):
    d, _ = foot
    assert px(d, "LOOK", 1.0, (160, 5)).max() < 20          # letterbox bar
    c = px(d, "LOOK", 1.9)                                   # a bright frame (grey ~94), so halving red shows
    assert c[2] < c[1] - 10                                  # red channel halved by matchColor


def test_audio_helpers(foot):
    f = foot[1]
    assert abs(f["jcutIn"] - 1.5) <= 0.04 and f["jcutVideoOff"] and f["bAudio"] is False   # in points snap to frames (1.5 s = f37.5)
    assert abs(f["duckAt15"] + 12) < 0.01 and abs(f["duckAt3"]) < 0.01 and f["fadeAt0"] <= -40
    assert f["punchAt15"] > f.get("punchBase", 100) * 1.25   # 130% of the fitted scale from 1.0 s


def test_transitions_render(foot):
    d, _ = foot
    assert px(d, "TRANS", 0.5)[2] > 200 and px(d, "TRANS", 1.5)[1] > 200   # red, then green after the whip
    assert px(d, "TRANS", 2.0).max() < 40                                    # the dip to black at the second cut
    assert px(d, "TRANS", 2.5)[0] > 200


def test_colormatch_end_to_end_in_effectcraft(tmp_path):
    """footage.py colormatch -> matchColor() in EffectCraft must pull a tinted image back toward the reference"""
    rng = np.random.default_rng(5)
    ref = cv2.GaussianBlur(rng.integers(40, 210, (240, 320, 3), dtype=np.uint8), (15, 15), 0)
    tinted = np.clip(ref.astype(int) * [0.75, 0.9, 1.2] + [0, 5, 20], 0, 255).astype(np.uint8)
    cv2.imwrite(str(tmp_path / "ref.png"), ref); cv2.imwrite(str(tmp_path / "tinted.png"), tinted)
    r = subprocess.run([sys.executable, str(R / "scripts" / "footage.py"), "colormatch", "ref.png", "tinted.png"], cwd=tmp_path,
                       capture_output=True, text=True)
    match = json.loads(r.stdout)
    (tmp_path / "cm.jsx").write_text(
        f'#include "{(R / "jsx" / "helpers.jsx").as_posix()}"\n#include "{(R / "jsx" / "footage.jsx").as_posix()}"\n'
        f'W = 320; H = 240; var MATCH = {json.dumps(match)};\n'
        'var cwd = new File(".").fsName.replace(/\\\\/g, "/").replace(/\\/\\.?$/, "") + "/";\n'
        'var c = comp("CM", 1, "#000000"); var l = placeClip(c, cwd + "tinted.png", 0, 1, 0); matchColor(l, MATCH); fxCheck();\n'
        'app.project.save(new File(cwd + "_cm.ecproj")); writeLn("CM OK");\n')
    out = build(tmp_path / "cm.jsx", tmp_path)
    assert "CM OK" in out, out
    subprocess.run([CLI, "render-frame", "--project", "_cm.ecproj", "--comp", "CM", "--time", "0.5", "--out", "out.png"], cwd=tmp_path, capture_output=True)
    got = cv2.imread(str(tmp_path / "out.png")).astype(float)
    before = np.abs(tinted.mean((0, 1)) - ref.mean((0, 1))).max()
    after = np.abs(got.mean((0, 1)) - ref.mean((0, 1))).max()
    assert after < before / 2, (before, after)


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
