# Fidelity levels: what a recreation may claim

Name only the level the current evidence proves, and say which tool proved it. "Exact copy" and "pixel perfect"
are not levels: resolve them to one below. Recreations here use original art, so a reference and a candidate never
share pixels; absolute MAE/PSNR/SSIM are not pass marks. Use them for structure (cuts, lead/lag, worst frames) and
to compare rounds against each other.

| Level | Claim | Evidence required |
|---|---|---|
| 1. Timebase locked | same size, fps, frame count, duration, start | `probe.py REF MINE` prints `timebase: LOCKED` |
| 2. Cut aligned | every reference cut lands within ±1 frame | `framemetrics.py` ref cuts vs `framecmp.py` candidate cuts; boundary frames (cut-1, cut, cut+1) inspected in `worst.png` or a frame grid |
| 3. Camera aligned | per shot, zoom / roll / pan follow the reference | `camtrack.py` per-shot table within your declared margins (e.g. zoom ±0.05x, roll ±1°), `--curve` on the hero shots |
| 4. Visual aligned | timing, layout, motion, colour, type and lens match closely enough for human review | levels 1-3, plus: side-by-side grids at a declared interval, dense 1-frame grids around every transition, `framemetrics.py` lead/lag list empty or explained, luma per 0.5 s within ~30, accepted differences listed |
| 5. Style aligned | palette, motion grammar, rhythm, transition vocabulary, but not the exact shots | a written breakdown of the reference's language and where the edit uses it |

## Promise rules

- Sampled sheets locate problems; they never approve a range. Approve with every-frame tools (`framemetrics.py`, `glitchfind.py`, `edgeblack.py`) over the whole range.
- A green build log or a successful render is not evidence. Decode the delivered file and measure it.
- A level holds only for the range measured. When a shot is re-rendered, re-measure the frames before, at and after each join with the untouched neighbours.
- If a gate is red, say "not aligned at fN" and name the first failing frame. Don't average a failure away.
- State what original art replaced (characters, logos, lyrics). That is a declared difference, not a failure.
