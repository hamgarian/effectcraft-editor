# Assets: generate, cut, title

Every scene gets its own art. Plan the list per scene before building (environment, characters, props, posters,
stickers), generate it in batches, then cut and title it here. Reusing a background across scenes is a visible shortcut.

## Generating images
Any image model works (ChatGPT/Codex image generation, Gemini, a local model). Batch prompt file, one image per call:

```
Create each image below with your image tool, one per call, saved as PNG with exactly the given filename.
No text, letters, numbers, logos, brand names or watermarks anywhere. All characters are ORIGINAL designs: do not
base them on, or make them resemble, existing bands, cartoons, comics, games or franchises.
Style for all: <one paragraph: medium, line, palette, shading, era>. Characters: <name: 1-line look>, ...

1. portrait_<name>.png: head-and-shoulders portrait of <name>, centred, plain pure white background, square.
2. <scene>_wall.png: landscape 16:9 photo of <surface> shot straight on (no perspective, no floor), <details>. High resolution.
3. <prop>.png: a single <prop>, three-quarter view, plain pure white background.
```

Example with the Codex CLI, run from the asset folder:
`codex exec -s workspace-write --skip-git-repo-check - < _prompt.txt`. If the model reports "at capacity", rerun with a
prompt that lists only the missing files.

Rules that came from misses:
- **No text in generated art.** Models garble it. Set titles, labels and small print yourself (`scripts/title_art.py`, or EffectCraft text).
- **Plain white background** for anything you will cut out; `scripts/cutwhite.py` floods from the border, so white inside the subject stays.
- **Consistency:** generate the cast's portraits first, then point later prompts at those files ("look at portrait_kit.png and keep the design").
- **Shot straight on** for walls and surfaces that become 3D planes or textures (no perspective, no floor or sky).
- **Ask for the angle you need:** "seen from behind, standing still" beats animating a front view.
- **High resolution for push-ins:** generate at the largest size, build print-like objects (discs, labels) as vector art at 3x.
- **Original only:** no real bands, labels, logos, lyrics or album art, and no copyrighted music in output files. Make your own: a made-up band name and label, your crew's silhouettes.

## Footage and stills from libraries
`scripts/stock.py search "rainy street at night"` lists Wikimedia Commons files with their licence and author.
Keep the licence line next to each file you download and credit it where the licence asks.

## Cut, title, place
1. `python scripts/cutwhite.py art.png` -> `art_cut.png` (RGBA).
2. `python scripts/title_art.py cover.png cover_titled.png --title "DUSK" --font impact.ttf --band 0.2 --small "ISSUE 07"`.
3. In the build: cut-outs on photos go through `compositeCutout()`; 3D props and sets come from Blender (`scripts/blender/`).
