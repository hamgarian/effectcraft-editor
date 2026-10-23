# Formats, safe areas and exports

## Frame sizes (`FORMATS` in jsx/templates.jsx)
| preset | size | use |
|---|---|---|
| vertical | 1080x1920 | Reels, Shorts, TikTok, Stories |
| portrait | 1080x1350 | 4:5 feed posts |
| square | 1080x1080 | feeds, carousels |
| landscape | 1920x1080 | YouTube, web |
| classic | 1440x1080 | 4:3 looks (often letterboxed inside) |

Pick the format first, then frame for it: a 16:9 edit squeezed into 9:16 later loses its composition.
`socialReframe(comp, "vertical", {safe: true})` puts an existing comp into another format over a blurred fill and
draws the safe area as a guide layer.

## Safe areas (`SAFE`)
Platform buttons, captions and the username cover the edges of vertical video. Commonly used margins (check the
platform's current guides): vertical top 220, bottom 420, left 60, right 140 px; keep titles and faces inside.
Letterbox bars (e.g. 46 or 104 px on a 1080-high frame) are part of the look, not a safe area.

## Exports (`scripts/export.py PROJECT COMP PRESET OUT`)
| need | preset | notes |
|---|---|---|
| post to social | h264 | yuv420p; add music with `audio.py mux` |
| hand to an editor with transparency | prores | ProRes 4444 with alpha (verified: yuva444p12le) |
| web overlay with transparency | webm | VP9 with alpha (alpha_mode=1) |
| frames for compositing / Blender | png | RGBA sequence |
| looping preview, chat | gif | large files: keep it short |
| web/app animation | lottie | prints what Lottie can't carry (e.g. Linear Wipe, some feathers) |
| keep editing in Premiere / Resolve / Final Cut | xml / fcpxml / otio / edl / aaf | layers are pre-rendered to clips |
| reusable graphic with controls | `.ectemplate` | `essentialize()` + `exportTemplate()`; `effectcraft-cli render --template T --values v.json` |
| hand edits in the app | open | `export.py PROJECT COMP open` starts EffectCraft with the project |

`render-frame` is an RGB preview; anything that needs alpha goes through these presets.
