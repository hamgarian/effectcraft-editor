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
- Shapes must be geometrically right: a CD is a circle; non-uniform scale makes ovals.
- Every scene carries some small caption text.

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
