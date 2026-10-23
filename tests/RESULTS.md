# Test results (v0.3.0, 2026-10-23)

Run from a fresh `git clone`, Windows 11, Python 3.13, EffectCraft **0.16.0** portable (`EFFECTCRAFT_CLI` set),
Blender 5.0, Windows SAPI voices. The same suite also passed on EffectCraft 0.14.0.

```
python -m pytest tests -q
38 passed in 101.10s
  test_tools.py   measurement, style map, joins, ledger, doctor, cut-outs, titles, Blender shadow set
  test_audio.py   beats (120 BPM click track), SFX + mix + mux + cut sync, sync offset, captions, TTS
  test_engine.py  6 templates render, 2 centring checks, .ectemplate re-rendered with new values,
                  5 export presets verified (ProRes alpha, WebM alpha, PNG RGBA, Lottie, OTIO), tracking follows a target

python scripts/bundle.py tests/smoke.jsx _smoke.jsx && effectcraft-cli script _smoke.jsx --empty
SMOKE OK

effectcraft-cli script tests/repro_quirks.jsx --empty        (0.14.0 and 0.16.0)
PRESENT shape layer: property("Position") keys the first group, not the layer  (layer keys 0, group keys 2)
PRESENT keys less than one frame apart merge  (numKeys 1)
```

Engine upgrade check: a 292-item reel project built without errors on 0.16.0, and 7 frames spread across it rendered
bit-identical on 0.14.0 and 0.16.0 (mean difference 0.000, max 0).

On a real 400-frame reel pair (not included): `probe.py` -> `timebase: LOCKED`; `framemetrics.py --count 340` ->
21 reference cuts, worst frames f174-f179; `audio.py beats` -> 139.7 BPM; `audio.py cutsync REF REF` -> 20/37 cuts
within 1 frame of a beat or hit; `stylemap.py` -> 48 shots, 26/47 cuts on a beat/hit, intro palette #05141b / #ede7e2.
`stock.py search "rainy street at night"` returned Commons files with licences (network, not in the suite).
