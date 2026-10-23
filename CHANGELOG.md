# Changelog

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
