# Motion component catalog

A motion that was matched against a reference and passed review gets an entry here, so the next edit can reuse it
instead of rediscovering it. Each entry says what it is for, its inputs, its timing, how it is built, the evidence
that it works, and its limits. Keep a reusable **build** (helper or script) separate from a fixed **replay** of one
reference's frames: never present a replay as a parameterised component.

Entry format:

```
### <name>
use: <what content or moment it suits>
inputs: <parameters>
timing: <frames, at the edit's fps>
build: <helper / script / recipe>
evidence: <what measured or reviewed it, and when>
limits: <where it breaks>
```

## Runnable templates (`jsx/templates.jsx`)

Each returns a comp; `essentialize()` exposes named controls and `exportTemplate()` writes an `.ectemplate` that
`effectcraft-cli render --template T --values v.json` renders without a script. `tests/test_engine.py` renders all of them.

| function | what | controls |
|---|---|---|
| `lowerThird({name, role, accent})` | accent bar wipes in from the left, name wipes on, role rises; reversed exit | Name, Role |
| `titleCard({title, sub, bg, fg})` | title slams in with a 2-frame overshoot, subtitle rises, slow push | Title, Subtitle |
| `logoReveal({logo, bg})` | feathered circle mask grows from the centre, light sweep across the logo | Logo text |
| `kineticType({words, times})` | one word per beat, slam + alternating tilt, slow push (`times` from `audio.py beats`) | - |
| `textOrbit3D({text, radius})` | characters on a 3D ring turning once | - |
| `socialReframe(comp, preset, {safe})` | any comp into vertical / square / portrait over a blurred fill, safe-area guide | - |

## Patterns

### whip-cut
use: cutting between two shots with energy, keeping the eye on the incoming key element
inputs: outgoing shot, incoming shot, whip direction
timing: outgoing sharp on its last hold frame -> 1 blurred whip frame (outgoing still half in frame) -> incoming lands sharp with its key element already present
build: hold keys on both camera moves; one-frame Motion Blur / Radial Blur on the whip frame; incoming shot's first frame already final
evidence: reel 2 review rounds 12-19 (2026-10), frame grids against the reference
limits: needs 20+ fps; at 12 fps one whip frame reads as a glitch

### grid-to-close-up whip
use: from a grid of tiles to one tile filling the frame
inputs: grid comp, target tile, roll direction
timing: 4 frames: sharp hold, ONE perspective-bent sweep frame (moderate blur, shape still legible), ONE near-empty background frame with only a blurred card corner, close-up lands already tilted
build: 3D layer Y/X rotation keys on the grid + a camera push, a whip card shape on the empty frame
evidence: reel 2 intro f16-f20, re-measured 2026-10-23 (grid width 0.57 of frame on the hold)
limits: pushing the camera INTO the grid instead of bending it gives mush

### collage build
use: a dense mixed-media collage that assembles on the beat
inputs: 12-16 separate pieces sorted into back / mid / front
timing: each piece snaps in on its own frame; front pieces drift about 3x more than back ones
build: one layer per piece, hold-key opacity + a 2-frame scale settle, parallax per depth
evidence: reel 2 collage rebuild (the grouped version read empty in review)
limits: a single grouped cut-out zoomed into reads empty

### typed caption across shots
use: short lines of on-screen text that run over several shots
inputs: lines, the time of each word group, position
timing: word groups appear on the music's hits; the layer runs over the cut into the next shot
build: one text layer in the main comp with hold keys on Source Text, kept above the shots and below the letterbox
evidence: reel 2 still-life -> alley (5.0-6.2 s), matched the reference's cross-shot caption
limits: re-order it above later layers at the end of the build, or later shots cover it

### curtain split outro
use: ending on a title that splits apart
inputs: title words, drape shape, timing
timing: title writes on, a 4-frame glitch, then the drape opens from the centre over about 11 frames, pushing the words apart, then black
build: a drape shape at its real width (curved edges) scaled in X with an "in" ease, words moving outward on the same ease, grain + exposure flicker + scratches over it
evidence: reel 2 outro 15.3-17.1 s, frame grid against the reference
limits: don't scale a thin shape by thousands of percent (raster limit clips it)

### cut-out composited into a photo plate
use: a drawn or generated character standing in a photographed place
inputs: plate comp, cut-out comp (alpha), position, light direction
build: `compositeCutout()` in jsx/helpers.jsx (grade match, backlit shading, light wrap, cast + contact shadow, grain), then one grade over the shot
evidence: reel 2 alley f111 (user review: "generic PNG on top of PNG" before), luma 37 -> 49 vs ref 51 after tuning
limits: cast-shadow shape is a simple quad; a figure lit from the side needs castDir changed

### photoreal device on a desk
use: a phone, tablet or laptop showing an animated UI, shot like real footage
inputs: desk texture, UI frames rendered from EffectCraft, props, camera beats
build: `scripts/blender/phone_on_desk.py` (Cycles, HDRI fill, sun + off-screen shadow casters, smudged glass, a screen that takes light), placed with `imageSequence()`
evidence: reel 2 phone shot (user reviews: "looks like a 3D render", "the phone isn't receiving shadow"); `tests/test_tools.py` checks the cast shadow darkens the frame
limits: desk tone sets the shot's brightness; a dark desk measured luma 44 vs a light reference's 55
