---
name: effectcraft-editor
description: Make motion-design edits in EffectCraft (the open-source After Effects-like compositor) by writing JSX build scripts, rendering headless, and checking the result with measurements instead of by eye; photoreal 3D sets come from headless Blender. Use for any EffectCraft edit, for recreating or matching a reference video/reel/ad, for directing an original motion edit, for compositing cut-outs into photos, or when a render looks wrong (black edges, ghosts, empty frames, wrong camera, wrong colours, "looks like CG", "pasted on").
metadata:
  version: 0.2.0
---

# effectcraft-editor

Build edits as a JSX script you can rerun, render frames headless, then measure against the reference (or against
your plan) and fix what the numbers flag. Tested on EffectCraft 0.14.0 (Windows x64 portable) and Blender 5.0.
Read `references/quirks.md` and `references/operating.md` before writing a script: most first-render bugs are
engine quirks listed there.

## Tools

- **EffectCraft CLI** (`effectcraft-cli`; set `EFFECTCRAFT_CLI` if not on PATH): `script build.jsx --empty` builds,
  `render-frame --project P --comp C --frame N --out f.png` renders one frame, `commands --filter X` and
  `exec effect.list --params "{\"filter\":\"X\"}"` list commands and effects with their parameters. It also ships an
  MCP server (`effectcraft-cli mcp`). See `references/operating.md`.
- **`jsx/helpers.jsx`**: `comp`, `place`, `K` (keys with measured ease presets), `P` (transform-safe property lookup),
  `fx` + `fxCheck` (effects; the build fails on an unresolved name), `shapeGroup`, `dashes`, `stepped`, `boil`,
  `infiniteBackground`, `imageSequence` (a rendered PNG sequence as layers), `compositeCutout` (cut-out into a photo
  plate). Headless scripts can't `#include`: bundle first.
- **`scripts/`** (Python 3.10+, `opencv-python`, `numpy`; ffmpeg/ffprobe on PATH):

| Script | Answers |
|---|---|
| `bundle.py IN.jsx OUT.jsx` | inlines `#include` lines so the headless CLI can run it |
| `bracecheck.py X.jsx` | unbalanced braces, or a `//` comment that swallows the rest of a line; run before every build |
| `render_seq.ps1 -Project edit.ecproj -Comp Main -Frames 400 [-Fps 20] -Out out.mp4 [-Seq dir]` | one process per frame (batch render runs out of memory) into `seq_<Comp>/`, then encode |
| `probe.py REF MINE [--sha FILE..]` | timebase lock: size, fps, frame count, duration, start, pixel format side by side; SHA-256 of delivered copies |
| `framestudy.py VIDEO OUT.png F0 F1 [--pick x,y ...]` | labelled frame grid, letterbox size, eyedropper colours |
| `framecmp.py REF MINE` | cut times and offsets, brightness/colour per 0.5 s |
| `framemetrics.py REF MINE [--out DIR]` | every frame: MAE/PSNR/SSIM, worst frames (sheet), frames around every reference cut, frames that lead/lag the reference |
| `camtrack.py REF MINE shots.json [--curve names]` | camera zoom / roll / pan per shot, or per frame |
| `glitchfind.py SEQ_DIR [--fps=N]` | one-frame pops (a frame unlike both neighbours) |
| `edgeblack.py SEQ_DIR [REF.mp4] [--fps=N]` | frames where black shows at the borders |
| `cutwhite.py IMG..` | cut generated art off a plain white background (keeps white inside the subject) |
| `fxprobe.jsx` | what an effect name resolves to in this EffectCraft, with its parameter names |
| `blender/kit.py`, `blender/phone_on_desk.py` | photoreal Blender sets: Cycles + HDRI + sun, off-screen shadow casters, smudged materials, screens that take light, UI image sequences, camera beats |

## Workflow

0. **Declare the contract**: copy `references/report-template.md` to `alignment-report.md` beside the project and fill in reference range, target
   fidelity level (`references/fidelity.md`), deliverables, declared differences, the evidence that approves it.
   No reference? Direct first: `references/director.md` (one moving idea, a beat table where every beat changes state,
   a slideshow check).
1. **Lock the timebase and study the reference frame by frame, from frame 0.** `probe.py`, then `framestudy.py` grids of
   every frame, not shot summaries. Write down: format (letterbox, active aspect), appearance order, every colour
   (eyedropper), what moves (camera vs elements), and for each transition how it was likely made. Measure the
   reference's brightness per 0.5 s before choosing a grade.
2. **Plan assets per scene before building.** Each scene gets its own environment and props; high-resolution assets with
   real small print. Generate art without text, add text yourself (`references/rules.md` -> Assets). Photo-like scenes
   and devices: a Blender set (`references/rules.md` -> Photoreal 3D). Original art and text only; no logos, lyrics or
   copyrighted music in outputs.
3. **Build** one script, one comp per shot, a main comp that places shots on the reference's cut times. End the script
   with `fxCheck()`. Run `bracecheck.py`, `bundle.py`, then `effectcraft-cli script _bundle.jsx --empty`. **Stop if the
   build output doesn't show your own success line**: otherwise you will render and review the previous project.
4. **Render** with `render_seq.ps1`; spot-check single frames with `render-frame` while iterating.
5. **Measure, then fix**: `framecmp` / `framemetrics` (cuts within 1 frame, lead/lag explained, luma within ~30),
   `camtrack` (zoom/roll/pan per shot), `edgeblack`, `glitchfind`, side-by-side grids of the same frames, then dense
   1-frame grids around transitions. Fix the earliest failing frame first, one cause at a time; log it in the patch log.
6. **Loop per shot.** When parameter tuning stops moving the numbers for 2 rounds, rebuild the shot's structure
   (`references/rules.md`) instead of tuning further. After re-rendering a range, re-check the frames at its joins.
7. **Approve only what the evidence proves** (`references/fidelity.md`): decode the delivered file, re-measure it, and
   name the level. Add shots that passed to `references/components.md`.
8. AI reviewers (video models, a second agent) are useful, but their claims are hypotheses: check the frames before
   acting on one. They repeat stale findings and invent things.

## Rules

`references/rules.md` holds the compositing, 3D, asset, motion and transition rules, each from a concrete miss. Short version:

- Match format and colours first; grey-ish means wrong.
- Animate only what the reference animates (camera vs elements); no shake it doesn't have.
- Comic/print look: per-panel colour grade clipped to the panel, plus halftone/noise texture.
- Cut-outs go INTO the plate: matched grade, light-direction shading, light wrap, cast + contact shadow, grain.
- Photo-like scenes: real 3D sets in Blender Cycles with shadow casters; every object, screens included, receives the shadow.
- Device screens: the UI on the device in one continuous shot.
- Infinite background behind every shot, never behind overlays.
- Overlays (viewfinder, UI) go above grade and vignette, crisp and full white.
- Curved motion on curved paths; dashed curves; on-twos stepping for a hand-made feel.
