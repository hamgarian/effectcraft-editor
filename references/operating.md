# Operating EffectCraft from an agent

Engine facts and traps for driving EffectCraft through its CLI or MCP server. Parts adapted from
[Vinciux99/effectcraft-claude-skill](https://github.com/Vinciux99/effectcraft-claude-skill) (MIT) and ideas from
[full-aigc-skills/effectcraft-skills](https://github.com/full-aigc-skills/effectcraft-skills) (Apache-2.0); checked
here against EffectCraft 0.14.0 and 0.16.0 where marked.

## Discover, don't guess
- Commands and their parameters: `effectcraft-cli commands --filter <word>` (add `--json`). Unknown keys are rejected and the error lists the accepted ones.
- Effects and their parameters: `effectcraft-cli exec effect.list --params "{\"filter\":\"blur\"}"` -> id, display name, every parameter with type, range and default. (0.14.0, checked)
- In JSX, `addProperty()` accepts the **display name** ("Hue/Saturation"), the **id** ("ec.color.huesaturation") or the AE match name ("ADBE HUE SATURATION"). A mixed form ("ADBE Hue/Saturation") resolves to nothing. Use the names `effect.list` prints, and end every build with `fxCheck()`. (0.14.0, checked; `scripts/fxprobe.jsx`)
- If a needed effect doesn't exist (no Light Wrap, Color Halftone, Gradient Map in 0.14.0), build it from parts (see `compositeCutout()` for light wrap) and say so. Never substitute a similar-named effect silently.

## Engine commands from a script
`app.run(id, params)` runs any engine command inside a JSX build; `run()` in helpers wraps it and records failures for
`fxCheck()`. Checked on 0.14.0:
- tracking: `track.new {layer, kind, position, target}` -> `track.setPoint {point: 1, center, featureSize, searchSize}` -> `track.analyze {wait: true}` -> `track.apply` (`trackAttach()`); also `track.mask`, `track.camera`, `track.warpStabilizer` (`stabilize()`), face tracking models.
- Essential Graphics: `essential.addProperty {comp, layer: NAME, path: "text/sourceText", name}` (address layers by name: an index went to the wrong layer), `essential.exportTemplate {comp, path}`.
- property paths look like `text/sourceText`, `transform/opacity`, `effects/#1/blurriness` (`effectcraft-cli props --project P COMP LAYER --flat` lists them).

## Interfaces
- **CLI, headless**: `script build.jsx --empty`, `render-frame`, `props`, `get`, `set`, `exec <id> --params <json>`. What these recipes use.
- **MCP**: `effectcraft-cli mcp` (headless; add `--autosave`, or call `save_project` at milestones, or the work lives only in memory) or `mcp --bridge 9877` to drive an open app started with `--control 9877`. The live bridge exits if the app isn't running when the agent starts.
- MCP `render_frame {time, max_side}` returns a PNG for a quick look; `batch` runs several commands as one undo step and rolls back if one fails.

## Traps
- **Layer time vs comp time**: MCP `add_keyframe` / `set_property` with `time` use layer time; reading and rendering use comp time. For moved layers pass `timeBase: "comp"`. In JSX `setValueAtTime` is comp time.
- **Alpha**: `render-frame` is an RGB preview. For a transparent handoff render to an RGBA PNG sequence; an MP4 never carries alpha.
- **Delivery is the decoded file**: a zero exit code or a "render complete" line proves nothing. Save, reopen the project, decode the output, and measure it (`probe.py`, `framemetrics.py`).
- **Timeouts are unknown, not failed**: if a command or render times out, inspect the project and the output before re-running an edit; replaying a non-idempotent edit doubles it.
- **Stale builds**: if a build fails, the previous project is still on disk. Stop the round when the build output lacks your success line; otherwise you render and review old work.
- Scripts may only read inside the project folder; writing files needs the scripting preference. Locked layers are skipped by commands. After opening a project, check for missing footage.
- **Windows**: PowerShell mangles quotes in JSON arguments to native programs; put the JSON in a file or a here-string, or run the call from Python. A blank or crashing window on start: try `WGPU_BACKEND=vulkan` (or `dx12`) for one launch.
