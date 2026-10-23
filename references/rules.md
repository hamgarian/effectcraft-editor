# Editing rules

Each rule came from a concrete miss on a reference recreation that a human reviewer caught.

## Fidelity
- Study frame by frame from frame 0. Frame 0 often has content (a motion-blurred card).
- Match the format first: letterbox bar heights, active picture aspect. They can change per section (e.g. 104 px in the intro, 46 px later).
- Match appearance order exactly, including flickers and disappearances between appearances.
- Eyedropper every colour from the reference. Grey-ish means wrong.
- Measure exposure per reference; never carry a previous project's grade over. If a fix overshoots, interpolate between the two passes.
- If the reference moves only the camera, don't animate the elements, and vice versa. No shake unless it's there.
- Look for duplicate-outline layers (offset outline copies) and other overlays on top of the main image.
- Hero framing: rule of thirds or centred exactly as the reference; check head position per frame.

## Compositing
- Comic/print look: a colour grade clipped to each panel (track or alpha matte) plus noise/halftone texture over it. Characters take on the panel colour; they don't sit pasted on top. Halftone: a copy of the art with CC Ball Action (grid spacing about 5) multiplied at about 20%.
- Speed/paint splashes: white organic strokes (simple shapes plus noise displacement), never flat geometric shards.
- Photo-like scenes: a real 3D scene, with a 3D wall and floor, image planes on the wall, lights casting shadows, and a camera with depth of field. With only a 2D plate, add a shadow-catcher plane.
- Physical props read better as real 3D models (e.g. from Blender) than as 2D cut-outs. Small blurred foreground props sell the space.
- Device UI: one continuous shot with the UI corner-pinned into the device (inset about 10% for the bezel). Never cut to a flat UI rectangle. Keep the camera from showing the photo's edge.
- Every scene gets its own environment and props; don't reuse the last scene's background.
- Infinite background: behind each shot, a frame-sized solid of its background colour (or a blurred 240% copy for photo shots), spanning the shot's in/out. Skip overlays (blend modes, partial or animated opacity, flash/dim/fade/wipe layers), or they turn into solid blocks.
- Overlays (viewfinder, UI chrome) sit above grade and vignette: crisp, full white.
- Shapes must be geometrically right: a CD is a circle; non-uniform scale makes ovals. Build print-like objects (discs, labels, posters) as vector art at 3x so macro push-ins stay crisp.
- Every scene carries some small caption text. A typed caption can run across a cut into the next shot (the reference may do this on purpose).
- **Cut-out into a photo plate, never "PNG on PNG".** Grade the plate toward the reference first. Then match the cut-out's black and white points and saturation to the plate, shade it for the plate's light (backlit means darker front, lit at the top), add light wrap (the blurred plate through an edge band inside the silhouette), a cast shadow in the light's direction plus tight contact shadows at the feet, the plate's softness and grain, and finally one grade over the whole shot. `compositeCutout()` does all of it.
- Screen/insert composites: get perspective and occlusion right first, then the mask, then match brightness, colour temperature and blur; keep reflections; check the edges frame by frame while anything moves.

## Photoreal 3D (Blender sets)
- "Make it a real 3D scene" means it must pass as footage. Eevee with flat lights reads as CG. Use Cycles (GPU, denoised), an HDRI for bounce light and reflections (Blender ships some in `datafiles/studiolights/world`), the AgX view transform, and imperfections everywhere: bevels on every edge, bump and roughness variation from noise (smudged glass, worn metal, wood grain), small real props (a cable, a mug, buttons).
- **Shadows sell it.** Put off-screen shadow casters (a wall edge, a window bar, a branch) between the sun and the set, invisible to camera and reflections, placed along the sun direction so a clear soft-edged shadow lands where the reference has one. Keep the HDRI fill low (about 0.15) or the sun/shade contrast washes out.
- **Every object must receive the shadow, devices included.** A pure-black self-lit screen ignores light, so the shadow seems to skip the phone. Give the display a diffuse base that sunlight washes out and a slightly rough smudged coat. Verify with a sun-only render (world strength 0) that the shadow edge actually crosses the object.
- Kill reflection hotspots by rotating the HDRI (its window reflects in glass) rather than turning off the sun's reflections (that also removes the sun's sheen on the glass).
- Set brightness in the render (camera exposure), not with a gamma lift in EffectCraft: a lift greys the blacks and flattens shadow edges. The set's base tones (a dark desk vs a light one) decide the shot's brightness more than exposure does.
- Animated UI on a 3D device: build the UI in EffectCraft, render that comp to PNGs, show them on the screen frame by frame, render the set, and place it back as an image sequence. The UI stays editable in one place.

## Assets
- Image models can't be trusted with text: generate art with no text, logos or watermarks, then set titles and small print yourself (PIL or EffectCraft text). Fit titles to both width and band height, or they clip.
- Generate on plain white and cut with `scripts/cutwhite.py` (flood fill from the border keeps white inside the subject).
- New scenes get new assets (walls, props, posters); a reused background is a visible shortcut.

## Motion and transitions
- Ease presets measured from reference camera moves (temporal ease influence): snap 92, out 72, soft 60, in 33, linear 4. `K(prop, keys, "snap")`.
- Camera on twos (Posterize Time at half rate) for a hand-made feel; the camera can stay at full rate while elements step.
- Curved motion follows curved paths (bezier); arrows are curves with the head riding the path. Dashed curved lines are a common motif.
- Mixed-media letters get subtle paper texture; static art "boils" (a few px of turbulent displacement re-randomised 8 times a second).
- **Whip-cut between shots:** the outgoing shot stays sharp on its last hold frame, gets ONE blurred whip frame while still half in frame, and the incoming shot lands sharp with its key element already present.
- **Grid-to-close-up whip (4 frames):** a sharp hold, ONE big perspective-bent sweep frame (moderate blur, shape still legible), ONE near-empty background frame with only a blurred corner of the card, then the close-up lands already tilted. Pushing the camera into the grid instead gives mush.
- Collage: 12-16 separate pieces at 3 depths (back posters, mid characters, front stickers), each snapping in on its own frame; front pieces drift about 3x more than back ones. A single grouped cut-out zoomed into reads empty.
- Depth of field on hero shots (blurred top/bottom band or edges).
- Outros: vintage film, glitch, curtain transitions when the reference has them; make dedicated assets for them.
- Re-measure a framing that was marked "verified" when something feels off. A wrong note ("grid about 1/3 of frame width", really 0.57) survived several rounds because every later key was relative to it.

## Review loop
- Sampled sheets (every 0.5 s) locate problems; dense 1-frame grids around fast motion and transitions find them; every-frame tools approve a range (`references/fidelity.md`).
- Keep `alignment-report.md` (template in `references/report-template.md`): the contract, the current numbers, the first failing frame, and a patch log.
- When a shot passes review, add it to `references/components.md` so the next edit reuses it.
