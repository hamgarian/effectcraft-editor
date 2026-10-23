# Test results (v0.1.0, 2026-10-23)

Run from a fresh `git clone` of this folder, Windows 11, Python 3.13, EffectCraft 0.14.0 portable.

```
python -m pytest tests -q
8 passed in 16.74s

python scripts/bundle.py tests/smoke.jsx _smoke.jsx && effectcraft-cli script _smoke.jsx --empty
SMOKE OK

effectcraft-cli script tests/repro_quirks.jsx --empty
PRESENT shape layer: property("Position") keys the first group, not the layer  (layer keys 0, group keys 2)
PRESENT keys less than one frame apart merge  (numKeys 1)
```
