"""Report where curly-brace depth is not zero at a top-level statement (finds an unclosed or extra brace).
Usage: python bracecheck.py FILE.jsx
"""
import re
import sys

STR = re.compile(r'"(\\.|[^"\\])*"|\'(\\.|[^\'\\])*\'')
depth = 0
OPEN = 0
for i, line in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    s = STR.sub('""', line).split("//")[0]
    if re.match(r"^(function |var |// ----------)", line) and depth != 0:
        print(f"line {i}: depth {depth} at a top-level statement -> {line.rstrip()[:80]}")
        depth = 0
    depth += s.count("{") - s.count("}")
    OPEN += s.count("[") + s.count("(") - s.count("]") - s.count(")")
    if "//" in STR.sub(chr(34) * 2, line) and OPEN > 0 and not re.search(r"^\s*//", line):
        print(f"line {i}: // comment while ( or [ is still open -> the rest of the expression may be commented out")
    if re.match(r"^(function |var |// ----------)", line) and OPEN == 0:
        pass
print("end depth", depth, "paren/bracket", OPEN)
