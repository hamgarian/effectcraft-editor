"""ec_cli.py: finding and saving the EffectCraft CLI, with a fake CLI (no EffectCraft needed, real env untouched)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

S = Path(__file__).resolve().parent.parent / "scripts"


def fake_cli(d, ver="9.9.9"):
    if os.name == "nt":
        p = d / "effectcraft-cli.cmd"; p.write_text(f"@echo EffectCraft {ver} (headless), 731 commands, 307 effects\n")
    else:
        p = d / "effectcraft-cli"; p.write_text(f"#!/bin/sh\necho 'EffectCraft {ver} (headless)'\n"); p.chmod(0o755)
    return p


def run(*args, env=None):
    # Windows env names are case-insensitive: normalise so an override replaces the real variable, not sits beside it
    merged = {k.upper(): v for k, v in os.environ.items()}
    merged.update({k.upper(): v for k, v in (env or {}).items()})
    return subprocess.run([sys.executable, str(S / "ec_cli.py"), *map(str, args)], capture_output=True, text=True, env=merged)


def test_env_var_wins_and_reports_version(tmp_path):
    p = fake_cli(tmp_path)
    r = run(env={"EFFECTCRAFT_CLI": str(p)})
    assert r.returncode == 0 and str(p) in r.stdout and "EffectCraft 9.9.9" in r.stdout, r.stdout + r.stderr


def test_not_found_tells_the_agent_to_ask(tmp_path):
    bogus = tmp_path / "nope.exe"
    r = run(env={"EFFECTCRAFT_CLI": str(bogus), "PATH": str(tmp_path), "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
                 "ProgramFiles": str(tmp_path), "ProgramFiles(x86)": str(tmp_path), "LOCALAPPDATA": str(tmp_path), "SystemRoot": os.environ.get("SystemRoot", "")})
    if r.returncode == 0:
        pytest.skip("a real EffectCraft sits in a fixed install folder on this machine")
    assert "NOT FOUND" in r.stdout and "Ask the user" in r.stdout and "--set" in r.stdout


def test_set_validates_and_saves(tmp_path):
    p = fake_cli(tmp_path)
    bad = run("--set", tmp_path / "missing-cli", "--dry-run")
    assert bad.returncode != 0 and "Nothing saved" in (bad.stdout + bad.stderr)
    if os.name == "nt":   # never change the real user environment in a test
        ok = run("--set", p, "--dry-run")
        assert ok.returncode == 0 and "would run" in ok.stdout and "EFFECTCRAFT_CLI" in ok.stdout, ok.stdout + ok.stderr
    else:
        rc = tmp_path / "rc"; rc.write_text("export EFFECTCRAFT_CLI=/old\nexport OTHER=1\n")
        ok = run("--set", p, env={"EC_RC_FILE": str(rc)})
        assert ok.returncode == 0
        text = rc.read_text()
        assert f'export EFFECTCRAFT_CLI="{p}"' in text and "/old" not in text and "export OTHER=1" in text
