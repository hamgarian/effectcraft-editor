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


def test_framemetrics_flags_lag_cut_and_worst(vids, tmp_path):
    # mine = ref delayed by 2 frames over the push-in; the flat grey section after the cut is too dark
    out = run("framemetrics.py", vids / "ref.mp4", vids / "mine.mp4", "--out", tmp_path / "m")
    summary = json.loads(out.splitlines()[0])
    assert summary["ref_cuts"] == [25], summary
    assert summary["max_mae"] > 100  # grey 200 vs 60
    assert (tmp_path / "m" / "worst.png").exists() and (tmp_path / "m" / "metrics.json").exists()
    lagged = zoom_frames(25, 1.3, texture())
    write(tmp_path / "lag.mp4", lagged[:2] + lagged[:-2])
    out2 = run("framemetrics.py", vids / "ref.mp4", tmp_path / "lag.mp4", "--count", "20")
    assert json.loads(out2.splitlines()[0])["temporal_mismatches"] > 10, out2


def test_probe_locks_and_flags(vids):
    out = run("probe.py", vids / "ref.mp4", vids / "ref.mp4", "--sha", vids / "ref.mp4")
    assert "timebase: LOCKED" in out and "sha256 " in out
    write(vids / "short.mp4", zoom_frames(10, 1.0, texture()))
    assert "mismatch" in run("probe.py", vids / "ref.mp4", vids / "short.mp4")


def test_framemetrics_baseline_marks_codec_noise(vids, tmp_path):
    out = run("framemetrics.py", vids / "ref.mp4", vids / "ref.mp4", "--baseline")
    s = json.loads(out.splitlines()[0])
    assert "codec_floor_p95" in s and s["frames_above_codec_floor"] == 0, s


def test_joincheck_flags_jump_and_repeat(tmp_path):
    for i in range(20):   # a steadily moving bar
        img = np.zeros((90, 160, 3), np.uint8); cv2.rectangle(img, (i * 6, 20), (i * 6 + 20, 70), (255, 255, 255), -1)
        cv2.imwrite(str(tmp_path / f"f_{i:05d}.png"), img)
    assert "seams clean" in run("joincheck.py", tmp_path, "--joins", "10")
    cv2.imwrite(str(tmp_path / "f_00010.png"), cv2.imread(str(tmp_path / "f_00009.png")))   # a repeated frame at the seam
    r = subprocess.run([sys.executable, str(S / "joincheck.py"), tmp_path, "--joins", "10"], capture_output=True, text=True)
    assert r.returncode == 1 and "REPEATED" in r.stdout, r.stdout


def test_stylemap_shots_and_table(vids, tmp_path):
    out = run("stylemap.py", vids / "ref.mp4", tmp_path / "s")
    s = json.loads(out.splitlines()[0])
    assert s["shots"] == 2, s   # the push-in, then the flat grey after the cut at f25
    table = (tmp_path / "s" / "stylemap.md").read_text()
    assert "push in" in table and (tmp_path / "s" / "shots.png").exists()


def test_ledger_flags_unfinished_and_changed(tmp_path):
    led = tmp_path / "l.jsonl"; f = tmp_path / "out.txt"; f.write_text("v1")
    rid = run("ledger.py", "start", "render", "--ledger", led).strip()
    assert "UNKNOWN" in run("ledger.py", "status", "--ledger", led)
    run("ledger.py", "end", rid, "--outputs", f, "--ledger", led)
    assert " ok " in run("ledger.py", "status", "--ledger", led)
    f.write_text("v2")
    r = subprocess.run([sys.executable, str(S / "ledger.py"), "verify", "--ledger", str(led)], capture_output=True, text=True)
    assert r.returncode == 1 and "changed" in r.stdout


def test_title_art_fits_band(tmp_path):
    cv2.imwrite(str(tmp_path / "a.png"), np.full((400, 300, 3), 230, np.uint8))
    run("title_art.py", tmp_path / "a.png", tmp_path / "b.png", "--title", "VERY LONG TITLE HERE", "--band", "0.2")
    ink = np.where(cv2.imread(str(tmp_path / "b.png"))[:, :, 0] < 128)
    assert ink[0].size > 0 and ink[0].max() < 0.2 * 400   # the title stays inside its band...
    assert ink[1].min() > 0 and ink[1].max() < 299        # ...and inside the width
    run("title_art.py", tmp_path / "a.png", tmp_path / "c.png", "--label", "NIGHT BUS")
    assert (cv2.imread(str(tmp_path / "c.png"))[20, 30] < 40).all()   # black label strip drawn


def test_doctor_runs(tmp_path):
    r = subprocess.run([sys.executable, str(S / "doctor.py")], capture_output=True, text=True)
    assert "python" in r.stdout and ("ready" in r.stdout or "missing" in r.stdout)


def test_cutwhite_keeps_inner_white(tmp_path):
    img = np.full((120, 120, 3), 255, np.uint8)
    cv2.circle(img, (60, 60), 40, (0, 0, 200), -1)
    cv2.circle(img, (60, 60), 12, (255, 255, 255), -1)  # white INSIDE the subject must survive
    cv2.imwrite(str(tmp_path / "s.png"), img)
    run("cutwhite.py", tmp_path / "s.png")
    a = cv2.imread(str(tmp_path / "s_cut.png"), cv2.IMREAD_UNCHANGED)[:, :, 3]
    assert a[5, 5] == 0 and a[60, 60] == 255 and a[60, 30] == 255


def blender_exe():
    import os
    import shutil
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    found = shutil.which("blender")
    if found:
        return found
    hits = sorted(Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"))
    return str(hits[-1]) if hits else None


@pytest.mark.skipif(blender_exe() is None, reason="Blender not installed (set BLENDER=path)")
def test_phone_set_casts_a_shadow_across_the_frame(tmp_path):
    """the off-screen wall edge must leave the left of the wide shot clearly darker than the right"""
    rng = np.random.default_rng(3)
    desk = cv2.resize(rng.integers(120, 170, (32, 64, 3), dtype=np.uint8), (512, 256), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(tmp_path / "desk.png"), desk)
    (tmp_path / "ui").mkdir()
    for i in range(2):
        cv2.imwrite(str(tmp_path / "ui" / f"ui_{i:04d}.png"), np.full((171, 90, 3), 30, np.uint8))
    r = subprocess.run([blender_exe(), "-b", "-P", str(S / "blender" / "phone_on_desk.py"), "--", "--desk", str(tmp_path / "desk.png"),
                        "--ui-dir", str(tmp_path / "ui"), "--out", str(tmp_path / "r"), "--frames", "0-0", "--res", "240x180", "--samples", "8"],
                       capture_output=True, text=True, timeout=900)
    out = tmp_path / "r" / "frame_0000.png"
    assert out.exists(), r.stdout[-2000:] + r.stderr[-2000:]
    g = cv2.cvtColor(cv2.imread(str(out)), cv2.COLOR_BGR2GRAY).astype(float)
    left, right = g[:, :60].mean(), g[:, -60:].mean()
    assert left < right * 0.75, (left, right)


def test_bracecheck_flags_comment_eating_braces(tmp_path):
    (tmp_path / "bad.jsx").write_text("function f() { if (x) { y(); // note } }\nvar z = 1;\n")
    out = run("bracecheck.py", tmp_path / "bad.jsx")
    assert "depth 2 at a top-level statement" in out
    (tmp_path / "ok.jsx").write_text("function f() { if (x) { y(); } }\nvar z = 1;\n")
    assert "end depth 0" in run("bracecheck.py", tmp_path / "ok.jsx")
