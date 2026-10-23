<p align="center"><img src="logo.svg" width="96" alt=""></p>

# effectcraft-editor `v0.1.0`

**Result:** on one reel recreation these tools took the measured gaps to the reference down. Grid camera zoom went from 0.45x to 0.71x (ref 0.70x), a dive from 0.85x to 1.00x (ref 1.00x), intro letterbox from 0 to 104 px (ref 104 px), and frames flagged for wrong brightness from 18 to 0.
The measurements are from the build logs and weren't rerun for this repo. The tests that were run are in `tests/RESULTS.md`.

An agent skill for making motion-design edits in EffectCraft (the open-source,
After Effects-like compositor) that hold up next to a reference: build with a JSX script, render headless,
then **measure** cuts, camera moves, exposure, exposed edges and one-frame glitches against the reference
and fix what the numbers flag.

It came out of recreating two motion-design reels with original art. Every rule in
`references/rules.md` and every quirk in `references/quirks.md` comes from a miss that a human reviewer
caught or that broke a render.

This is a guide, not a discovery. Related projects:
[full-aigc-skills/effectcraft-skills](https://github.com/full-aigc-skills/effectcraft-skills) (16 skills,
generates projects from plans) and
[Vinciux99/effectcraft-claude-skill](https://github.com/Vinciux99/effectcraft-claude-skill) (operating
manual and MCP setup). Neither README (checked 2026-10-23) describes reference matching or measurement.

## Quickstart

```bash
git clone <this repo> effectcraft-editor && cd effectcraft-editor
pip install opencv-python numpy pytest
python -m pytest tests -q
```

Copy the folder to where your agent loads skills (Claude Code: `~/.claude/skills/effectcraft-editor`).
Put `effectcraft-cli` on PATH or set `EFFECTCRAFT_CLI` to its full path. Needs ffmpeg on PATH for encoding.

Check the JSX helpers against your EffectCraft:

```bash
python scripts/bundle.py tests/smoke.jsx _smoke.jsx
effectcraft-cli script _smoke.jsx --empty
```

It should print `SMOKE OK`.

## What's inside

- `SKILL.md`: the workflow (study frame by frame, plan assets, build, render, measure, loop per shot).
- `references/rules.md`: compositing, motion and transition rules (whip-cut grammar, clipped grades, 3D scenes, infinite background, measured ease presets).
- `references/quirks.md`: EffectCraft 0.14 scripting quirks and workarounds, plus which effects exist.
- `jsx/helpers.jsx`: build-script helpers.
- `scripts/`: measurement and build tools (see the table in `SKILL.md`).

## Limits

- Tested on EffectCraft 0.14.0, Windows x64. Quirks may be fixed in later versions.
- `camtrack.py` reads big foreground motion as camera motion; trust it on shots where the background dominates.
- `render_seq.ps1` is PowerShell; on other systems loop `effectcraft-cli render-frame` the same way.

MIT licence.
