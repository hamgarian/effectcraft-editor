"""Inline `#include "<path>"` lines into one script, because effectcraft-cli (0.14, headless) refuses to
read included files: its scripting sandbox doesn't know the script's folder when run from the CLI.
Usage: python bundle.py build.jsx _bundle.jsx
"""
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
inc = re.compile(r'^\s*(?://@|#)include\s+"([^"]+)"\s*$', re.M)


def expand(path, seen):
    path = path.resolve()
    if path in seen:
        raise SystemExit(f"include cycle at {path}")
    text = path.read_text(encoding="utf-8")
    return inc.sub(lambda m: expand((path.parent / m.group(1)) if not Path(m.group(1)).is_absolute() else Path(m.group(1)), seen | {path}), text)


out = expand(src, set())
dst.write_text(out, encoding="utf-8", newline="\n")
print(f"bundled {src} -> {dst} ({out.count(chr(10))} lines)")
