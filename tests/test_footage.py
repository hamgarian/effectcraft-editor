"""footage.py on synthetic clips with known answers. Run: python -m pytest tests -q"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

S = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(S))


def run(*args, cwd=None):
    r = subprocess.run([sys.executable, str(S / "footage.py"), *map(str, args)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("clips")
    # 2 s of moving test pattern, hard cut at 2.00 s to 2 s of a different scene; tone, 1 s silence, tone
    ff("-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=2", "-f", "lavfi", "-i", "mandelbrot=size=320x240:rate=25",
       "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
       "-f", "lavfi", "-i", "sine=frequency=660:duration=1.5",
       "-filter_complex", "[1:v]trim=duration=2,setpts=PTS-STARTPTS[m];[0:v][m]concat=n=2:v=1[v];"
       "[3:a]atrim=duration=1,asetpts=PTS-STARTPTS[s];[2:a][s][4:a]concat=n=3:v=0:a=1[a]",
       "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "4", d / "talk.mp4")
    return d


def test_probe_and_conform_fix_vfr(clips, tmp_path):
    # variable frame rate: frames at irregular times, like phone footage
    ff("-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=3", "-vf", "setpts='PTS+0.02*sin(N)/TB'", "-fps_mode", "vfr",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", tmp_path / "vfr.mp4")
    out = run("conform", tmp_path / "vfr.mp4", tmp_path / "cfr.mp4", "--fps", 25)
    p = json.loads(out.strip().splitlines()[-1])
    assert p["fps"] == 25.0 and not p["vfr"], p


def test_scenes_finds_the_cut(clips):
    shots = json.loads(run("scenes", clips / "talk.mp4"))
    assert len(shots) == 2 and abs(shots[0]["out"] - 2.0) <= 0.08, shots


def test_silences_keep_the_talk(clips, tmp_path):
    keep = json.loads(run("silences", clips / "talk.mp4", "--pad", "0.05"))
    assert len(keep) == 2, keep
    assert abs(keep[0]["out"] - 1.55) < 0.12 and abs(keep[1]["in"] - 2.45) < 0.12, keep


def test_colormatch_brings_a_tinted_frame_back(tmp_path):
    rng = np.random.default_rng(2)
    ref = cv2.GaussianBlur(rng.integers(30, 220, (120, 160, 3), dtype=np.uint8), (9, 9), 0)
    tinted = np.clip(ref.astype(int) * [0.7, 0.9, 1.25] + [0, 10, 25], 0, 255).astype(np.uint8)   # BGR: warmer, brighter red
    cv2.imwrite(str(tmp_path / "ref.png"), ref); cv2.imwrite(str(tmp_path / "t.png"), tinted)
    run("colormatch", tmp_path / "ref.png", tmp_path / "t.png", "--out", tmp_path / "m.json", "--cube", tmp_path / "m.cube")
    import footage
    lv = json.loads((tmp_path / "m.json").read_text())["levels"]
    fixed = footage.apply_levels(tinted, lv)
    before = np.abs(tinted.mean((0, 1)) - ref.mean((0, 1))).max()
    after = np.abs(fixed.mean((0, 1)) - ref.mean((0, 1))).max()
    assert after < before / 3, (before, after)
    cube = (tmp_path / "m.cube").read_text().splitlines()
    assert cube[1] == "LUT_3D_SIZE 33" and len(cube) == 2 + 33 ** 3


def test_reframe_follows_the_subject(tmp_path):
    vw = cv2.VideoWriter(str(tmp_path / "wide.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 25, (640, 360))
    for i in range(75):   # a bright subject crossing from left to right
        f = np.full((360, 640, 3), 40, np.uint8); x = 80 + i * 6
        cv2.circle(f, (x, 180), 40, (230, 230, 230), -1); vw.write(f)
    vw.release()
    k = json.loads(run("reframe", tmp_path / "wide.mp4", "--aspect", "9:16"))
    xs = [x for _, x in k["center_x"]]
    assert xs[-1] - xs[0] > 150 and all(b >= a - 2 for a, b in zip(xs, xs[1:])), xs   # follows, smoothly, one way


def test_beatcut_puts_cuts_on_beats(clips, tmp_path):
    import wave
    sr = 44100; a = np.zeros(sr * 4)
    for k in range(8):
        i = int(k * 0.5 * sr); a[i:i + 800] += np.sin(np.linspace(0, 200, 800)) * np.exp(-np.linspace(0, 8, 800))
    with wave.open(str(tmp_path / "m.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 20000).astype("<i2").tobytes())
    cuts = json.loads(run("beatcut", tmp_path / "m.wav", clips / "talk.mp4", clips / "talk.mp4"))
    assert len(cuts) >= 5
    assert all(abs((c["out"] - c["in"]) - 0.5) < 0.05 for c in cuts), cuts
    assert all(abs(c["at"] - round(c["at"] / 0.5) * 0.5) < 0.05 for c in cuts), cuts


def test_normalize_hits_target(clips, tmp_path):
    ff("-i", clips / "talk.mp4", "-af", "volume=-18dB", "-c:v", "copy", tmp_path / "quiet.mp4")
    run("normalize", tmp_path / "quiet.mp4", tmp_path / "loud.mp4", "--lufs", "-16")
    sys.path.insert(0, str(S))
    import audio
    i, _ = audio.lufs(str(tmp_path / "loud.mp4"))
    assert abs(i - (-16)) < 1.5, i
