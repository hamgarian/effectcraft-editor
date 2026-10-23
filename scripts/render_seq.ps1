# One EffectCraft process per frame (batch `render` runs out of memory on long comps), then ffmpeg encode.
# Usage: .\render_seq.ps1 -Project edit.ecproj -Comp Main -Frames 400 -Fps 20 -Out out.mp4 [-Cli path\to\effectcraft-cli.exe]
# -Cli defaults to $env:EFFECTCRAFT_CLI, then effectcraft-cli on PATH.
param([string]$Project, [string]$Comp, [int]$Frames, [int]$Fps = 20, [string]$Out, [string]$Seq = "seq_$Comp",
      [string]$Cli = $(if ($env:EFFECTCRAFT_CLI) { $env:EFFECTCRAFT_CLI } else { "effectcraft-cli" }))
New-Item -ItemType Directory -Force $Seq | Out-Null
Remove-Item "$Seq\f_*.png" -ErrorAction SilentlyContinue
$failed = @()
for ($n = 0; $n -lt $Frames; $n++) {
  $f = "{0}\f_{1:D5}.png" -f $Seq, $n
  for ($try = 0; $try -lt 3 -and -not (Test-Path $f); $try++) { & $Cli render-frame --project $Project --comp $Comp --frame $n --out $f 2>&1 | Out-Null }
  if (-not (Test-Path $f)) { $failed += $n }
}
"failed frames: $($failed -join ',')"
ffmpeg -v error -y -framerate $Fps -i "$Seq\f_%05d.png" -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p -movflags +faststart $Out
"encoded $Out"
