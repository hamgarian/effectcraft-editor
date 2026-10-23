# Setup on Windows, macOS and Linux

Run `python scripts/doctor.py` first: it checks everything below and prints the fix for what is missing.

## EffectCraft
Download from the [EffectCraft releases](https://github.com/storytold/effectcraft/releases).
- **Windows**: the portable zip or the installer; `effectcraft-cli.exe` sits next to `effectcraft.exe` (not on PATH).
- **macOS**: the app image holds the app; the CLI is a separate download (`effectcraft-cli-*-macos-*.zip`). Unzip it, clear quarantine (`xattr -dr com.apple.quarantine effectcraft-cli`).
- **Linux**: use the deb, rpm or tar.gz (an AppImage holds only the app). Headless servers without a GPU need Vulkan software drivers (e.g. mesa-vulkan-drivers).
Then `python scripts/ec_cli.py` finds it (env var, PATH, install folders, unpacked zips in Downloads/Desktop/Documents).
If it doesn't, or picks an old copy, save the right one: `python scripts/ec_cli.py --set <path to effectcraft-cli>`
(a Windows user environment variable, or an `export` line in `~/.zshrc` / `~/.bashrc`; open a new terminal afterwards).
A blank or crashing window on start: try `WGPU_BACKEND=vulkan` (or `dx12` on Windows) for one launch.

## Python and tools
Python 3.10+, `pip install opencv-python numpy pillow pytest certifi`, ffmpeg + ffprobe on PATH.
Optional: Blender 4.2+ (photoreal sets; `BLENDER=path`), Piper or espeak-ng (narration; Windows and macOS have built-in voices),
whisper (caption timing from speech).

## MCP (optional, for live inspection)
The CLI is also an MCP server. Claude Code:
```
claude mcp add --scope user effectcraft -- "<path to effectcraft-cli>" mcp --autosave
```
For a live window: start the app with `effectcraft --control 9877`, then register `mcp --bridge 9877` instead; the live
server exits if the app isn't running when the agent starts. Claude Desktop: add the same command and args under
`mcpServers` in `claude_desktop_config.json` (double the backslashes on Windows). The control channel listens on
127.0.0.1 with no authentication: close the app when you're done.

## Install the skill
Copy this folder to your agent's skills folder (Claude Code: `~/.claude/skills/effectcraft-editor`), then run
`python -m pytest tests -q` there. Engine tests skip without `EFFECTCRAFT_CLI`, the Blender test without Blender.
