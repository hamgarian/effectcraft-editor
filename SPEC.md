# SPEC: effectcraft-editor

Goal: an agent skill that lets one prompt produce a good EffectCraft edit, especially one that
matches a reference video, by building with JSX scripts and checking results with measurements.

Inputs: a request (and optionally a reference video). Outputs: a JSX build script, a rendered
video, and measurement reports comparing it with the reference.

## Acceptance
- [x] `SKILL.md` has kebab-case `name` and a `description` saying what it does and when to trigger.
- [x] No hardcoded user paths, project names or fixed frame rate in scripts (CLI via `-Cli`/`EFFECTCRAFT_CLI`; fps read from the video or `--fps=`).
- [x] `pytest tests` passes: camtrack zoom, camtrack needs shots, framecmp cut + exposure, glitchfind, edgeblack, framestudy letterbox, bundle (+cycle), bracecheck.
- [x] `tests/smoke.jsx` prints `SMOKE OK` on EffectCraft 0.14.0 (helpers: place, P on shape layers, dashes, ease keys, infiniteBackground skips overlays).
- [x] Every quirk in `references/quirks.md` lists a workaround; ones reproduced by a minimal script say "Verified".
- [x] Rules in `references/rules.md` are general (no reel-specific names or copyrighted material).
- [x] Runs from a fresh `git clone` (same machine; see `tests/RESULTS.md`). Not tested on a second machine.
