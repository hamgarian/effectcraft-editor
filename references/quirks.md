# EffectCraft scripting quirks (0.14.0)

Each one caused a visible bug in a real build. "Verified" = reproduced by `tests/repro_quirks.jsx` on
0.14.0 (output in `tests/RESULTS.md`); the rest were seen during builds and fixed by the workaround shown.

| Quirk | Workaround |
|---|---|
| On a shape layer, `layer.property("Position")` (and Scale, Opacity...) hits the **first shape group's** transform once groups exist. Verified. | `layer.property("ADBE Transform Group").property("Position")`; `P()` in helpers does this. |
| Keyframes less than one frame apart merge into one. Verified. | Space hold keys at least `1/fps` apart. |
| The first group in a shape layer's Contents draws on top. | `group.moveTo(1)` after adding (`shapeGroup()`). |
| Cameras only move 3D layers; a camera move over 2D layers does nothing. | `threeDLayer = true` on everything the camera should move. |
| `#include` is refused by `effectcraft-cli script` (no script folder / sandbox). | `scripts/bundle.py`. Don't loosen the scripts-may-write-files preference to get around it. |
| Batch `render` runs out of memory on long comps (died near frame 240 every time). | `render_seq.ps1`: one `render-frame` process per frame. Don't rebuild the project while it renders. |
| A layer parented to a precomp layer uses the precomp's **top-left** as origin. | Centre is `[w/2, h/2]`, not `[0,0]`. |
| Set `startTime` before `inPoint`/`outPoint`; a source comp shorter than the layer's out-point renders empty frames at the end. | `place()` sets them in order; make source comps at least as long as their use. |
| Fractal Noise as a matte: Brightness moves the edge by roughly brightness / contrast. | Scale the brightness sweep with contrast (contrast 1800 needed about -1000 to 850). |
| Motion blur on hold-key jumps and 2-frame scale slams produces double images. | Leave those layers out of motion blur. |
| Camera Lens Blur with a Blur Map renders the map layer even when the map layer is disabled. | Depth-of-field band: an adjustment layer with Gaussian blur and a LUMA track matte of the band map (white = blur). |
| Keying white (`colorkey=0xFFFFFF`) on a white object deletes the object. | Put a white shape under the cut-out, or generate on a contrasting background. |
| A `//` comment after `{` on a one-line block comments out the closing braces; a `//` inside an open `(` or `[` eats the rest of the expression. | Comments on their own line; `bracecheck.py` before every build. The same happens when an agent inserts a note mid-line in a Python set script (`# note` hid a material assignment: blank white screen). Comments only at the end of a finished line. |
| An effect name that doesn't resolve fails silently: `fx()` logs one line among hundreds and the build "succeeds". `"ADBE Hue/Saturation"` matched nothing for several rounds. Verified. | Names from `exec effect.list`; `fxCheck()` at the end of the build throws on any failure; `scripts/fxprobe.jsx` shows what a name resolves to. |
| A thin shape scaled by thousands of percent (a 20 px drape at 9000% X) clips at a raster size limit: only part of it renders. | Draw the shape at its real size and scale less (500%). |
| A Linear Wipe on a text layer wipes the text BOX, which is wider than the ink, so a write-on appears late. | Start the wipe before the layer's visible start (e.g. 0.25 s early). |
| `render-frame` output is RGB. | For alpha, render an RGBA PNG sequence with `render` (or `scripts/export.py` presets). |
| A null is a 100 px square anchored at [50,50]: children placed at [0,0] sit 50 px up-left of the null's position. Verified (title and kinetic type rendered at x 0.46, y 0.42 of frame). | Reset the null's Anchor Point to [0,0] (`rig()` in templates.jsx). |
| Text sits on its baseline, so "centred" text renders above centre. | Anchor on the measured ink: `sourceRectAtTime(0,false)` -> anchor = rect centre (`text()` in templates.jsx does it). |
| `essential.addProperty` with a layer INDEX resolved to a different layer ("no property text/sourceText"). | Address layers by unique name. |
| `track.motion` only creates a tracker (0 keys). | `track.new` -> `track.setPoint` -> `track.analyze {wait:true}` -> `track.apply` (`trackAttach()`). |

## Effects seen working in 0.14.0

CC Radial Fast Blur, ADBE Radial Blur, CC Radial Blur, ADBE Motion Blur, ADBE Stroke, ADBE Linear Wipe,
ADBE Venetian Blinds, ADBE Radio Waves, CC Scatterize, Turbulent Displace, Posterize Time, Easy Levels2,
Tint, Fill, Find Edges, Tritone, Mosaic, Roughen Edges, Gaussian Blur 2, Ramp, CC Ball Action (halftone),
CC Page Turn, Fractal Noise, native stroke dashes (`ADBE Vector Stroke Dashes` > Dash 1 / Gap 1).

Also resolving in 0.14.0 (`fxprobe.jsx`): Hue/Saturation, Color Balance, Photo Filter, Exposure, Minimax, Matte Choker,
Simple Choker, Glow, Vibrance, Black & White, Channel Blur, Set Matte, Shift Channels, Curves, Color Balance (HLS).

Not available: Color Halftone, Gradient Map, Write-on (use a Linear Wipe on the text layer), Light Wrap / CC Light Wrap
(build it: `compositeCutout()`).
