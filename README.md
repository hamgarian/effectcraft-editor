<p align="center"><img src="logo.svg" width="96" alt=""></p>

# effectcraft-editor `v0.2.0`

**Result:** on one reel recreation these tools took the measured gaps to the reference down. Grid camera zoom went from 0.45x to 0.71x (ref 0.70x), a dive from 0.85x to 1.00x (ref 1.00x), intro letterbox from 0 to 104 px (ref 104 px), and frames flagged for wrong brightness from 18 to 0. On a second reel, `framemetrics.py` named the worst stretch on its own (f174-179, a CD macro push that stops short), which a separate AI review of the same render had also flagged.
These measurements and the review come from the project's build and review logs, which aren't in this repo and weren't rerun. The tests that were run are in `tests/RESULTS.md`.

An agent skill for making motion-design edits in EffectCraft (the open-source, After Effects-like compositor) that
hold up next to a reference: build with a JSX script, render headless, then **measure** cuts, camera moves,
exposure, exposed edges, one-frame glitches and per-frame structure against the reference, and fix what the numbers
flag. Photo-like scenes come from photoreal Blender sets placed back in the edit.

It came out of recreating two motion-design reels with original art. Every rule in `references/rules.md` and every
quirk in `references/quirks.md` comes from a miss that a human reviewer caught or that broke a render.

## How it compares

This is a guide, not a discovery. Checked 2026-10-23 from each project's README and file list (not run):

| | this repo | [Pluviobyte/video-production-skills](https://github.com/Pluviobyte/video-production-skills) | [full-aigc-skills/effectcraft-skills](https://github.com/full-aigc-skills/effectcraft-skills) | [Vinciux99/effectcraft-claude-skill](https://github.com/Vinciux99/effectcraft-claude-skill) |
|---|---|---|---|---|
| target | EffectCraft (+ Blender sets) | HyperFrames / Remotion | EffectCraft | EffectCraft |
| recreate a reference | yes, frame by frame | yes (replica + QC) | no | no |
| per-frame metrics, worst / boundary / lead-lag frames | yes | yes (MAE, PSNR, SSIM, hashes) | no | no |
| camera move per shot (zoom / roll / pan) | yes | not described | no | no |
| fidelity levels and promise rules | yes | yes | no (delivery checks: save, reopen, decode) | no |
| direct an original edit | beat table + slideshow check | motion director skill | genre templates (logo reveal, lower thirds, ...) | no |
| compositing / photoreal 3D rules | yes, from reviews | no | screen-composite skill | no |
| engine setup, MCP, command catalog | pointers | n/a | pinned installer, 655 commands | setup scripts, MCP guide |

Ideas taken from them: fidelity levels, a written contract, every-frame approval and a component catalog
(Pluviobyte); save-reopen-decode delivery checks, timeouts as unknown, never substituting a similar-named effect
(full-aigc); discovery commands, layer vs comp time, alpha and Windows traps (Vinciux99, MIT, adapted in
`references/operating.md`). No code or text was copied. If you also install full-aigc's set, note that it has a skill
with the same name (`effectcraft-editor`, an embedded editor launcher); install one of them under a different folder name.

## Quickstart

Needs Python 3.10+, ffmpeg and ffprobe on PATH, and [EffectCraft](https://github.com/storytold/effectcraft/releases)
for the JSX checks (its CLI, `effectcraft-cli`, ships with it: put it on PATH or set `EFFECTCRAFT_CLI`). Blender is
optional (its test is skipped without it; set `BLENDER=path` if it isn't found).

```bash
git clone https://github.com/hamgarian/effectcraft-editor && cd effectcraft-editor
pip install opencv-python numpy pytest
python -m pytest tests -q
```

Copy the folder to where your agent loads skills (Claude Code: `~/.claude/skills/effectcraft-editor`).

Check the JSX helpers against your EffectCraft:

```bash
python scripts/bundle.py tests/smoke.jsx _smoke.jsx
effectcraft-cli script _smoke.jsx --empty
```

It should print `SMOKE OK`.

## What's inside

- `SKILL.md`: the workflow (contract, study frame by frame, plan assets, build, render, measure, loop per shot, approve).
- `references/rules.md`: compositing, photoreal 3D, asset, motion and transition rules.
- `references/quirks.md`: EffectCraft 0.14 scripting quirks and workarounds, plus which effects exist.
- `references/operating.md`: driving EffectCraft from an agent (discovery commands, MCP, traps).
- `references/fidelity.md`, `report-template.md`, `components.md`, `director.md`: what a recreation may claim, the running report, the catalog of proven motions, and directing an edit without a reference.
- `jsx/helpers.jsx`: build-script helpers, including `compositeCutout()` and `imageSequence()`.
- `scripts/`: measurement and build tools (table in `SKILL.md`), and `scripts/blender/` for photoreal sets.

## Limits

- Tested on EffectCraft 0.14.0 and Blender 5.0, Windows x64. Quirks may be fixed in later versions.
- With original art, absolute MAE/PSNR/SSIM are not pass marks; use them for cuts, lead/lag and worst frames, and to compare rounds.
- `camtrack.py` reads big foreground motion as camera motion; trust it on shots where the background dominates.
- `render_seq.ps1` is PowerShell; on other systems loop `effectcraft-cli render-frame` the same way.
- The Blender example is one set (a phone on a desk); other sets reuse `scripts/blender/kit.py`.

MIT licence.
