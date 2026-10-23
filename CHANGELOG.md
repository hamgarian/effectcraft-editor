# Changelog

## 0.3.0 — 2026-10-23
Closes the feature gaps found against Pluviobyte/video-production-skills, full-aigc-skills/effectcraft-skills,
Vinciux99/effectcraft-claude-skill, jhonsu01/effectcraft-mcp-server and OpenMontage.
- Audio: `scripts/audio.py` (beats + hits, original SFX bank, mix, mux, cut-to-beat check, loudness/peak/sync vs reference); `references/audio.md`.
- Templates: `jsx/templates.jsx` (lower third, title card, logo reveal, kinetic type, 3D text orbit, social reframe) with Essential Graphics controls and `.ectemplate` export; renders checked in `tests/test_engine.py`; `docs/templates.png`.
- Formats and handoff: `scripts/export.py` (h264, hevc, ProRes 4444 alpha, VP9 alpha, GIF, RGBA PNG, Lottie, FCP XML / FCPXML / OTIO / EDL / AAF, open in app), each verified after export; `references/formats.md` (sizes, safe areas).
- Engine coverage: `run`, `mask`, `expr`, `trackAttach`, `stabilize`, `captionTrack` helpers; tracking tested on a moving target.
- Reference style: `scripts/stylemap.py` (shots, measured camera, palette, energy, tempo -> a director beat table).
- QC: `framemetrics.py --baseline` (codec noise floor), `scripts/joincheck.py` (jumps, repeats, missing frames at seams); rebuild vs replay in `fidelity.md`.
- Assets: `references/assets.md` (prompt template, consistency, licences), `scripts/title_art.py`, `scripts/stock.py` (Wikimedia Commons with licences).
- Narration and captions: `scripts/tts.py` (Piper, Windows voices, macOS say, espeak), `scripts/captions.py` (SRT/VTT/JSX from lines, beats or whisper).
- Setup and recovery: `scripts/doctor.py`, `references/setup.md` (per OS, MCP), `scripts/render_seq.py` (any OS, resumable, retries), `scripts/ledger.py` (run ledger, UNKNOWN runs, changed outputs).
- Quirks: null anchors at [50,50], baseline-anchored text, essential controls need layer names, `track.motion` doesn't analyse.

## 0.2.0 — 2026-10-23
- Photoreal 3D: `scripts/blender/kit.py` (Cycles + denoise, HDRI fill, sun, off-screen shadow casters, smudge/wear materials, screens that take light, UI image sequences, camera beats, Blender 5 F-curve access) and `scripts/blender/phone_on_desk.py`; a test checks the cast shadow darkens the frame.
- Compositing: `compositeCutout()` (grade match, backlit shading, light wrap, cast + contact shadow, grain) and `imageSequence()` in `jsx/helpers.jsx`.
- Effects: `fx()` collects failures and `fxCheck()` fails the build on an unresolved effect name; `scripts/fxprobe.jsx`; names come from `exec effect.list` (display names and ids resolve, hybrid names don't).
- Measurement: `scripts/probe.py` (timebase lock, SHA-256) and `scripts/framemetrics.py` (every-frame MAE/PSNR/SSIM, worst frames sheet, cut boundaries, lead/lag).
- Assets: `scripts/cutwhite.py` (border flood-fill cut-out).
- References: `fidelity.md`, `report-template.md`, `components.md`, `director.md`, `operating.md`; rules for compositing, photoreal 3D, shadows on every object, brightness in the render, text on generated art; quirks for silent effect names, raster limit on giant scales, text-box wipes, RGB `render-frame`.
- Ideas adapted from Pluviobyte/video-production-skills, full-aigc-skills/effectcraft-skills and Vinciux99/effectcraft-claude-skill (see README).

## 0.1.0 — 2026-10-23
- First release: workflow skill, rules, EffectCraft 0.14 quirks, JSX helpers, 7 measurement/build scripts, pytest suite and a JSX smoke test.
