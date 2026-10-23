<p align="center"><img src="logo.svg" width="96" alt=""></p>

# effectcraft-editor `v0.3.0`

**Result:** on one reel recreation these tools took the measured gaps to the reference down. Grid camera zoom went from 0.45x to 0.71x (ref 0.70x), a dive from 0.85x to 1.00x (ref 1.00x), intro letterbox from 0 to 104 px (ref 104 px), and frames flagged for wrong brightness from 18 to 0. On a second reel, `framemetrics.py` named the worst stretch on its own (f174-179, a CD macro push that stops short), which a separate AI review of the same render had also flagged; `audio.py` read that reel's music at 139.7 BPM and found 26 of 47 cuts on a beat or hit.
These measurements and the review come from the project's build and review logs, which aren't in this repo and weren't rerun. The tests that were run are in `tests/RESULTS.md`.

An agent skill for making motion-design edits in EffectCraft (the open-source, After Effects-like compositor):
build with a JSX script, render headless, then **measure** cuts, camera moves, exposure, beats, exposed edges,
one-frame glitches and per-frame structure against a reference, and fix what the numbers flag. It also covers
original edits (director mode, a reference's style as a beat table, templates), sound (beats, effects, mix),
captions and narration, social formats, every EffectCraft export, tracking, compositing, and photoreal Blender sets.

<p align="center"><img src="docs/templates.png" alt="The six templates rendered headless by the test suite, including an .ectemplate re-rendered with new values"></p>

It came out of recreating two motion-design reels with original art. The rules in `references/rules.md` and the
quirks in `references/quirks.md` come from misses that a human reviewer caught or that broke a render.

## How it compares

This is a guide, not a discovery. Checked 2026-10-23 from each project's README, skill files and file list (none run).

| | this repo | [Pluviobyte/video-production-skills](https://github.com/Pluviobyte/video-production-skills) | [full-aigc-skills/effectcraft-skills](https://github.com/full-aigc-skills/effectcraft-skills) | [Vinciux99/effectcraft-claude-skill](https://github.com/Vinciux99/effectcraft-claude-skill) | [jhonsu01/effectcraft-mcp-server](https://github.com/jhonsu01/effectcraft-mcp-server) |
|---|---|---|---|---|---|
| engine | EffectCraft + Blender | HyperFrames / Remotion | EffectCraft | EffectCraft | EffectCraft (MCP) |
| recreate a reference, every-frame metrics | yes (+ camera per shot, codec baseline, joins) | yes (MAE/PSNR/SSIM, joins, codec baseline) | no | no | no |
| fidelity levels, contract, component catalog | yes | yes | delivery checks | no | no |
| original edit: director / reference style | beat table, slideshow check, `stylemap.py` | motion director | genre skills | no | no |
| templates with controls | 6 + `.ectemplate` export | 2 genre skills | 8 genre skills | no | 8 built-in + `.ectemplate` |
| music: beats, cut sync, SFX, mix | yes (`audio.py`) | typing SFX in one opener | no | no | audio layers |
| captions, narration, stock search | yes (SRT/VTT/burn-in, offline TTS, Commons) | no | no | no | no |
| formats + exports (alpha, ProRes, WebM, GIF, Lottie, timelines) | yes, verified after export | MP4 | yes | recipes | yes |
| tracking, masks, expressions | helpers (`trackAttach`, `mask`, `expr`) | n/a | skills | recipes | expressions |
| compositing + photoreal 3D rules | yes | no | screen composite | no | no |
| setup / doctor / MCP | `doctor.py`, `references/setup.md` | n/a | pinned installer | setup scripts | installer |
| crash recovery | run ledger (`ledger.py`), resumable renders | no | task ledger + recovery | no | no |

Ideas taken from them, written fresh: fidelity levels, a written contract, every-frame approval, codec baselines,
join checks and a component catalog (Pluviobyte); save-reopen-decode delivery, timeouts as unknown, never
substituting a similar-named effect, genre templates, a run ledger (full-aigc); discovery commands, layer vs comp
time, alpha and Windows traps, MCP setup (Vinciux99, MIT, adapted in `references/operating.md` and `setup.md`);
templates as `.ectemplate` with controls (jhonsu01); starting from a reference's style (OpenMontage). No code or text
was copied. full-aigc's set also has a skill named `effectcraft-editor` (an embedded-editor launcher): install one of
them under a different folder name.

## Quickstart

Needs Python 3.10+, ffmpeg and ffprobe on PATH, and [EffectCraft](https://github.com/storytold/effectcraft/releases)
(its CLI, `effectcraft-cli`: put it on PATH or set `EFFECTCRAFT_CLI`). Optional: Blender (photoreal sets), Piper or
espeak (narration on Linux; Windows and macOS voices are built in). `references/setup.md` has per-OS steps.

```bash
git clone https://github.com/hamgarian/effectcraft-editor && cd effectcraft-editor
pip install opencv-python numpy pillow pytest certifi
python scripts/doctor.py
python -m pytest tests -q
```

Engine tests run when `EFFECTCRAFT_CLI` is set, the Blender test when Blender is found; both skip otherwise.
Copy the folder to where your agent loads skills (Claude Code: `~/.claude/skills/effectcraft-editor`).

## What's inside

- `SKILL.md`: the workflow (contract, study, assets + audio, build, render, measure, loop, approve) and the tool table.
- `references/`: `rules.md` (compositing, 3D, assets, motion), `quirks.md` (EffectCraft 0.14), `operating.md` (commands, MCP, traps), `fidelity.md`, `report-template.md`, `components.md` (templates + proven motions), `director.md` (original edits, reference style), `audio.md`, `formats.md`, `assets.md`, `setup.md`.
- `jsx/helpers.jsx` (build helpers, compositing, tracking, captions) and `jsx/templates.jsx` (six templates, Essential Graphics controls, formats and safe areas).
- `scripts/`: measurement, audio, export, captions, narration, style map, render, ledger and setup tools; `scripts/blender/` for photoreal sets.

## Limits

- Tested on EffectCraft 0.14.0 and Blender 5.0, Windows x64. macOS/Linux steps follow the EffectCraft docs but weren't run here.
- With original art, absolute MAE/PSNR/SSIM are not pass marks; use them for cuts, lead/lag and worst frames, and to compare rounds.
- `camtrack.py` and `stylemap.py` read big foreground motion as camera motion; trust them where the background dominates.
- Beat detection is a spectral-flux tracker without ML: fine for pop/electronic, weaker on rubato or ambient music.
- Safe-area margins are commonly used values, not platform specs. No CapCut/JianYing draft export (use FCP XML / OTIO).

MIT licence.
