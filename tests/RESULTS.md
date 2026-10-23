# Test results (v0.2.0, 2026-10-23)

Run from a clean copy of this folder (no git history), Windows 11, Python 3.13, EffectCraft 0.14.0 portable,
Blender 5.0 (the Blender test renders one 240x180 frame and checks the cast shadow).

```
python -m pytest tests -q
12 passed in 19.63s

python scripts/bundle.py tests/smoke.jsx _smoke.jsx && effectcraft-cli script _smoke.jsx --empty
SMOKE OK

effectcraft-cli script tests/repro_quirks.jsx --empty
PRESENT shape layer: property("Position") keys the first group, not the layer  (layer keys 0, group keys 2)
PRESENT keys less than one frame apart merge  (numKeys 1)

effectcraft-cli script scripts/fxprobe.jsx --empty
YES  Hue/Saturation = ADBE HUE SATURATION -> ...
NO   ADBE Hue/Saturation
NO   Light Wrap
```

On a real 400-frame reel pair (not included): `probe.py` -> `timebase: LOCKED`; `framemetrics.py --count 340` ->
21 reference cuts found, worst frames f174-f179 (a macro push that stops short of the reference).
