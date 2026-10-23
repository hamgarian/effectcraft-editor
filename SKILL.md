---
name: effectcraft-editor
description: Make motion-design edits in EffectCraft (the open-source After Effects-like compositor) by writing JSX build scripts, rendering headless, and checking the result with measurements instead of by eye. Use for any EffectCraft edit, for recreating or matching a reference video/reel/ad in EffectCraft, for "make it look like this video", or when an EffectCraft render looks wrong (black edges, ghosts, empty frames, wrong camera, wrong colours).
metadata:
  version: 0.1.0
---

# effectcraft-editor

Build edits as a JSX script you can rerun, render frames headless, then measure against
the reference (or against your plan) and fix what the numbers flag. Tested on EffectCraft
0.14.0 (Windows x64 portable). Read `references/quirks.md` before writing a script: most
first-render bugs are engine quirks listed there.

## Tools

- **EffectCraft CLI** (`effectcraft-cli`; set `EFFECTCRAFT_CLI` if not on PATH):
  `script build.jsx --empty` builds a project, `render-frame --project P --comp C --frame N --out f.png`
  renders one frame, `props` / `get` inspect a project. EffectCraft also ships an MCP server
  (`effectcraft-cli mcp`); register it in your agent if you want live inspection.
- **`jsx/helpers.jsx`**: core helpers (`comp`, `place`, `K` keys with measured ease presets,
  `P` transform-safe property lookup, `fx`, `shapeGroup`, `dashes`, `stepped`, `boil`,
  `infiniteBackground`). Headless scripts can't `#include`: bundle first.
- **`scripts/`** (Python 3.10+, `opencv-python`, `numpy`; ffmpeg on PATH):

| Script | Answers |
|---|---|
| `bundle.py IN.jsx OUT.jsx` | inlines `#include` lines so the headless CLI can run it |
| `bracecheck.py X.jsx` | unbalanced braces, or a `//` comment that swallows the rest of a line; run before every build |
| `render_seq.ps1 -Project -Comp -Frames -Fps -Out` | one process per frame (batch render runs out of memory), then encode |
| `framestudy.py VIDEO OUT.png F0 F1 [--pick x,y ...]` | labelled frame grid, letterbox size, eyedropper colours |
| `framecmp.py REF.mp4 MINE.mp4` | cut times and offsets, brightness/colour per 0.5 s |
| `camtrack.py REF.mp4 MINE.mp4 shots.json [--curve names]` | camera zoom / roll / pan per shot, or per frame |
| `glitchfind.py SEQ_DIR [--fps=N]` | one-frame pops (a frame unlike both neighbours) |
| `edgeblack.py SEQ_DIR [REF.mp4] [--fps=N]` | frames where black shows at the borders |

## Workflow

1. **Study the reference frame by frame, from frame 0.** `framestudy.py` grids of every
   frame, not shot summaries. Write down: format (letterbox, active aspect), appearance
   order, every colour (eyedropper, never eyeball), what moves (camera vs elements),
   and for each transition how it was likely made (effect, matte, camera). Measure the
   reference's brightness per 0.5 s (`framecmp.py` ref vs ref) before choosing a grade.
2. **Plan assets per scene before building.** Each scene gets its own environment and
   props; high-resolution assets with real small print so push-ins stay crisp. Generate
   more assets rather than reuse. Original art and text only, no logos, lyrics or
   copyrighted music in outputs.
3. **Build** one script, one comp per shot, a main comp that places shots
   (`place`) on the reference's cut times. Run `bracecheck.py`, `bundle.py`, then
   `effectcraft-cli script _bundle.jsx --empty`. **Stop if the build output doesn't show
   your own success line**: otherwise you will render and review the previous project.
4. **Render** with `render_seq.ps1`. Spot-check single frames with `render-frame` while iterating.
5. **Measure, then fix**: `framecmp` (starting targets: cuts within 1 frame, luma within ~30), `camtrack`
   (zoom/roll/pan per shot), `edgeblack`, `glitchfind`, and side-by-side frame grids of the
   same frames. Fix what the numbers flag before asking a human to look.
6. **Loop per shot.** When parameter tuning stops moving the numbers for 2 rounds, rebuild the
   shot's structure (see `references/rules.md`) instead of tuning further.
7. AI reviewers (video-capable models, a second agent) are useful, but their claims are
   hypotheses: check the frames before acting on one. They repeat stale findings and invent
   things (music on a silent render).

## Rules

`references/rules.md` holds the compositing, motion and transition rules, each from a
concrete miss. The short version:

- Match format and colours first; grey-ish means wrong.
- Animate only what the reference animates (camera vs elements); no shake it doesn't have.
- Comic/print look: per-panel colour grade clipped to the panel, plus halftone/noise texture.
- Photo-like scenes: real 3D layers (wall, floor, planes, lights with shadows, DOF camera).
- Device screens: the UI pinned into the device photo/model in one continuous shot.
- Infinite background behind every shot, never behind overlays.
- Overlays (viewfinder, UI) go above grade and vignette, crisp and full white.
- Curved motion on curved paths; dashed curves; on-twos stepping for hand-made feel.
