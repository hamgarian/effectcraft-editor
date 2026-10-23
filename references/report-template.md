# Alignment report (keep beside the project, update every round)

So the goal survives without chat memory. Copy to `alignment-report.md`.

## Contract
- reference: <file>, range <f0>-<f1> (<t0>-<t1> s), fps <n>
- target level: <1-5 from references/fidelity.md>
- deliverables: <mp4 path, project path, sheets>
- declared differences: <original art instead of ..., no copyrighted music in outputs, ...>
- evidence required: <probe LOCKED; cuts ±1 f; camtrack margins; framemetrics lead/lag empty; luma within 30>

## Current state (round N, date)
| check | tool | result | pass |
|---|---|---|---|
| timebase | probe.py | | |
| cuts | framecmp.py / framemetrics.py | | |
| camera per shot | camtrack.py | | |
| exposed edges | edgeblack.py | | |
| one-frame pops | glitchfind.py | | |
| lead / lag | framemetrics.py | | |
| worst frames | framemetrics.py worst.png | | |

First failing frame: <fN, what>

## Patch log (newest first)
| round | shot / frames | change | why (which number or review note) | result |
|---|---|---|---|---|
