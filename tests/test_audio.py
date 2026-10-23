"""audio.py on synthetic signals. Run: python -m pytest tests -q"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np

S = Path(__file__).resolve().parent.parent / "scripts"
SR = 44100


def run(*args):
    r = subprocess.run([sys.executable, str(S / "audio.py"), *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def click_track(path, bpm=120, dur=8.0, offset=0.0, times=None):
    a = np.zeros(int(dur * SR))
    for t in (times if times is not None else [k * 60 / bpm for k in range(int(dur * bpm / 60) + 1)]):
        i = int((offset + t) * SR)
        if i < len(a) - 800:
            a[i:i + 800] += np.sin(np.linspace(0, 200, 800)) * np.exp(-np.linspace(0, 8, 800))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a * 20000).astype("<i2").tobytes())


def test_beats_finds_tempo_and_grid(tmp_path):
    click_track(tmp_path / "m.wav", 120)
    out = run("beats", tmp_path / "m.wav", "--fps", 25, "--out", tmp_path / "b.json")
    b = json.loads((tmp_path / "b.json").read_text())
    assert 116 <= b["bpm"] <= 124, out
    gaps = np.diff(b["beats"])
    assert abs(np.median(gaps) - 0.5) < 0.03
    assert b["beat_frames"][1] - b["beat_frames"][0] in (12, 13, 14)


def test_sfx_mix_mux_and_check(tmp_path):
    run("sfx", tmp_path / "sfx")
    for n in ("whoosh", "click", "impact", "riser", "pop", "swish"):
        assert (tmp_path / "sfx" / f"{n}.wav").exists()
    (tmp_path / "cues.json").write_text(json.dumps([{"t": 0.5, "sfx": "sfx/whoosh.wav"}, {"t": 1.0, "sfx": "sfx/impact.wav", "gain": -3}]))
    click_track(tmp_path / "m.wav", 120, 3.0)
    run("mix", "--cues", tmp_path / "cues.json", "--music", tmp_path / "m.wav", "--out", tmp_path / "mix.wav", "--duration", 3)
    vw = cv2.VideoWriter(str(tmp_path / "v.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 25, (64, 64))
    for i in range(75):
        vw.write(np.full((64, 64, 3), 40 if i < 25 else 200, np.uint8))   # cut at f25 = 1.0 s, on a beat
    vw.release()
    run("mux", tmp_path / "v.mp4", tmp_path / "mix.wav", tmp_path / "out.mp4")
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                                str(tmp_path / "out.mp4")], capture_output=True, text=True).stdout.strip()
    assert has_audio == "aac"
    sync = run("cutsync", tmp_path / "out.mp4", tmp_path / "m.wav")
    assert "1/1 cuts within" in sync, sync
    chk = run("check", tmp_path / "out.mp4", tmp_path / "out.mp4")
    assert "aligned within 20 ms" in chk and "LUFS" in chk, chk


def test_captions_lines_beats_whisper(tmp_path):
    (tmp_path / "s.txt").write_text("the last bus\nwe run for it now\nno stops\n")
    r = subprocess.run([sys.executable, str(S / "captions.py"), "lines", "s.txt", "--duration", "6", "--out", "c"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    srt = (tmp_path / "c.srt").read_text()
    assert srt.startswith("1\n00:00:00,500 --> ") and "we run for it now" in srt
    caps = json.loads((tmp_path / "c.jsx").read_text().split("=", 1)[1].rstrip(";\n"))
    assert caps[-1]["t1"] <= 6.0 and all(c["t1"] > c["t0"] for c in caps)
    (tmp_path / "b.json").write_text(json.dumps({"beats": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]}))
    subprocess.run([sys.executable, str(S / "captions.py"), "beats", "s.txt", "b.json", "--out", "cb"], cwd=tmp_path, check=True, capture_output=True)
    assert "00:00:01,500 --> 00:00:02,500" in (tmp_path / "cb.srt").read_text()
    (tmp_path / "w.json").write_text(json.dumps({"segments": [{"start": 1.2, "end": 2.0, "text": " hi there "}]}))
    subprocess.run([sys.executable, str(S / "captions.py"), "whisper", "w.json", "--out", "cw"], cwd=tmp_path, check=True, capture_output=True)
    assert "hi there" in (tmp_path / "cw.vtt").read_text()


def test_tts_makes_speech_if_an_engine_exists(tmp_path):
    sys.path.insert(0, str(S))
    import tts
    if not tts.engines() or tts.engines() == ["piper"]:
        import pytest
        pytest.skip("no TTS engine without a model")
    out = subprocess.run([sys.executable, str(S / "tts.py"), "the last bus", str(tmp_path / "n.wav")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    with wave.open(str(tmp_path / "n.wav")) as w:
        assert w.getnframes() / w.getframerate() > 0.4


def test_check_measures_offset(tmp_path):
    hits = [0.3, 0.9, 1.25, 2.0, 2.4, 3.1, 3.3, 4.2, 4.9, 5.3]   # irregular, like real music
    click_track(tmp_path / "a.wav", dur=6.0, times=hits)
    click_track(tmp_path / "b.wav", dur=6.0, times=hits, offset=0.2)   # mine starts 200 ms late
    out = run("check", tmp_path / "a.wav", tmp_path / "b.wav")
    assert "late by" in out and any(f"by {ms} ms" in out for ms in range(180, 221)), out
