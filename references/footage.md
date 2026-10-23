# Editing footage

For edits built from real clips (vlogs, talking heads, montages, product shots, event recaps). Analysis runs in
Python (`scripts/footage.py`, JSON out); the edit is built in JSX with `jsx/footage.jsx` (include after `helpers.jsx`).

## 1. Prep (before anything touches the timeline)
- `footage.py probe DIR`: every clip's duration, fps, size, rotation, audio. **Conform anything it flags**:
  variable frame rate (phones, screen recordings) drifts out of sync, and H.264 in the "High 4:4:4 Predictive"
  profile (any lossless x264) renders as black frames in EffectCraft 0.16 without an error.
- `footage.py conform IN OUT --fps 25`: constant frame rate, rotation baked, every frame a keyframe (frame-accurate
  seeking), 48 kHz AAC. `--proxy` for a fast half-size working copy; `--lut look.cube` bakes a LUT in.
- `footage.py normalize IN OUT --lufs -14`: loudness before mixing (two-pass, video copied).

## 2. Find the material
| need | command | gives |
|---|---|---|
| shots inside a long take | `footage.py scenes CLIP` | cut list of shots (EffectCraft's own Scene Edit Detection put a 2.00 s cut at 2.88 s; this one is tested to ±2 frames) |
| tighten a talking head | `footage.py silences CLIP --db -35 --min 0.4` | cut list of the parts with sound, padded 80 ms |
| a montage on the beat | `footage.py beatcut MUSIC CLIP...` | one clip per beat interval, each from that clip's busiest stretch, with `at` times |
| a vertical version | `footage.py reframe CLIP --aspect 9:16` | crop centre over time (faces, else motion), smoothed like a calm operator |
| clips that look alike | `footage.py colormatch REF TARGET` | Levels per channel (+ `--cube` 3D LUT) |

## 3. Build (jsx/footage.jsx)
| group | helpers |
|---|---|
| place | `importFootage`, `placeClip(c, file, srcIn, srcOut, at, {fit, speed})`, `fitLayer(l, c, "cover"/"contain")` |
| assemble | `assemble(c, cuts, {transition, dur})` (back to back, or at each cut's `at`), `slip(l, delta)` |
| time | `setSpeed(l, 2)` (time stretch), `speedRamp(l, [[t, speed], ...], {ease, blend})`, `freezeFrame(l, at, dur)`, `reverseClip(l)` |
| transitions | `crossfade` / `dip` / `whip` / `zoom` / `slide` / `glitch` (inside `assemble`, or `dipTo`, `whipCut`, `glitchCut`) |
| framing | `punchIn(l, t, 130)` (jump-cut zoom), `kenBurns`, `pip(c, l, [x, y, w, h], {border})`, `splitScreen(c, [a, b], "h2"/"v2"/"grid4")`, `applyReframe(c, l, keys)` |
| audio | `jCut(c, a, b, lead)`, `lCut(c, a, b, lag)`, `audioFade(l, in, out)`, `duck(music, ranges, -12)` |
| look | `matchColor(l, match)`, `look(l, "teal-orange"/"warm"/"cool"/"bw"/"faded"/"punchy", amount)`, `filmLook(c, {grain, vignette, bars})`, `timecodeBurn(c)` |
| motion | `stabilize(l)`, `trackAttach(src, target, [x, y])` (helpers.jsx) |

Every helper is checked by `tests/test_engine.py` on synthetic clips whose grey level encodes the frame number, so
a rendered pixel tells which source frame is showing (speed ramps, freezes, reverses, slips land within 2 frames).

## Editing rules
- **Cut on action or on the beat**, not on a pause; a cut inside a movement hides itself.
- **J and L cuts** make dialogue flow: hear the next shot 0.3-0.8 s early, or let a line finish over the next picture.
- **Punch-ins hide jump cuts** in a talking head: alternate 100% and 115-130% framings between cuts.
- **Speed ramps** go fast through the boring part and ease into the moment; turn on frame blending (`blend`) for slow motion of footage shot at normal speed.
- **Match colour before styling**: make the clips agree first (`colormatch`), then apply one look to everything (an adjustment layer).
- **Duck the music** 10-14 dB under speech; fade audio 2-6 frames at every hard cut to avoid clicks.
- In points snap to whole frames: at 25 fps, 1.5 s is frame 37.5 and lands at 1.48 s. Plan cuts in frames.
- Footage is someone's work: keep the licence (`stock.py` writes one beside each download) and credit it.
