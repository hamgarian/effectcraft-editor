"""Find effectcraft-cli on this machine, or save the path the user gives, so every tool (and every later session) finds it.

  python ec_cli.py                 print the CLI path and version; exit 1 if none found (then ASK THE USER for the path)
  python ec_cli.py --all           every working copy found, newest first
  python ec_cli.py --set PATH      check PATH runs, then save it as EFFECTCRAFT_CLI for this user:
                                   Windows: user environment variable; macOS/Linux: an export line in the shell profile
                                   (new terminals and agent sessions see it; the current one needs a restart)
  python ec_cli.py --set PATH --dry-run    show what would be saved, change nothing
Order: EFFECTCRAFT_CLI, PATH, the usual install folders, then a shallow scan of Downloads / Desktop / Documents
(portable zips get unpacked there). A candidate counts only if `effectcraft-cli info` answers "EffectCraft".
Library: from ec_cli import find_cli; find_cli() -> path or None
"""
import glob
import os
import platform
import re
import shutil
import subprocess
import sys

NAMES = ["effectcraft-cli.exe"] if os.name == "nt" else ["effectcraft-cli"]
HOME = os.path.expanduser("~")


def version(path):
    """'0.16.0' if path is a working effectcraft-cli, else None"""
    try:
        r = subprocess.run([path, "info"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"EffectCraft\s+(\d+(?:\.\d+)+)", r.stdout + r.stderr)
    return m.group(1) if m else None


def candidates():
    env = os.environ
    out = []
    if env.get("EFFECTCRAFT_CLI"):
        out.append(env["EFFECTCRAFT_CLI"])
    for n in NAMES + ["effectcraft-cli"]:
        w = shutil.which(n)
        if w:
            out.append(w)
    if os.name == "nt":
        roots = [env.get("ProgramFiles", r"C:\Program Files"), env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.join(env.get("LOCALAPPDATA", ""), "Programs"), env.get("LOCALAPPDATA", ""),
                 os.path.join(HOME, "scoop", "apps"), os.path.join(HOME, ".artcraft", "bin"), r"C:\Tools", r"D:\Tools"]
        pats = [os.path.join(r, "EffectCraft*", "**", "effectcraft-cli.exe") for r in roots if r] + \
               [os.path.join(r, "effectcraft*", "**", "effectcraft-cli.exe") for r in roots if r] + \
               [os.path.join(HOME, ".artcraft", "bin", "effectcraft-cli.exe")]
    elif platform.system() == "Darwin":
        pats = ["/Applications/EffectCraft*.app/Contents/MacOS/effectcraft-cli", os.path.join(HOME, "Applications/EffectCraft*.app/Contents/MacOS/effectcraft-cli"),
                os.path.join(HOME, ".artcraft/bin/effectcraft-cli"), "/usr/local/bin/effectcraft-cli", "/opt/homebrew/bin/effectcraft-cli"]
    else:
        pats = ["/usr/bin/effectcraft-cli", "/usr/local/bin/effectcraft-cli", "/opt/effectcraft*/**/effectcraft-cli",
                os.path.join(HOME, ".local/bin/effectcraft-cli"), os.path.join(HOME, ".artcraft/bin/effectcraft-cli"),
                os.path.join(HOME, "Applications/effectcraft*/**/effectcraft-cli")]
    for p in pats:
        out += glob.glob(p, recursive=True)
    for d in ("Downloads", "Desktop", "Documents"):   # unpacked portable zips: shallow, so this stays fast
        base = os.path.join(HOME, d)
        for depth in ("*", "*/*", "*/*/*"):
            for n in NAMES:
                out += [p for p in glob.glob(os.path.join(base, depth, n)) if "effectcraft" in p.lower()]
    seen, uniq = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if os.path.isfile(p) and k not in seen:
            seen.add(k); uniq.append(p)
    return uniq


def find_all():
    found = [(version(p), p) for p in candidates()]
    found = [(v, p) for v, p in found if v]
    key = lambda vp: tuple(int(x) for x in vp[0].split("."))
    env_first = [vp for vp in found if os.environ.get("EFFECTCRAFT_CLI") and os.path.normcase(vp[1]) == os.path.normcase(os.environ["EFFECTCRAFT_CLI"])]
    rest = sorted([vp for vp in found if vp not in env_first], key=key, reverse=True)
    return env_first + rest   # an explicit EFFECTCRAFT_CLI wins; otherwise the newest version


def find_cli():
    """fast path: a working EFFECTCRAFT_CLI, then PATH; the folder scan (and a version check per copy) only if neither works"""
    env = os.environ.get("EFFECTCRAFT_CLI")
    if env and version(env):
        return env
    for n in NAMES:
        w = shutil.which(n)
        if w and version(w):
            return w
    f = find_all()
    return f[0][1] if f else None


def save(path, dry=False):
    path = os.path.abspath(path)
    v = version(path)
    if not v:
        sys.exit(f"{path} is not a working effectcraft-cli (`info` did not answer EffectCraft). Nothing saved.")
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command", f"[Environment]::SetEnvironmentVariable('EFFECTCRAFT_CLI', '{path}', 'User')"]
        print(("would run: " if dry else "") + " ".join(cmd[3:]))
        if not dry:
            subprocess.run(cmd, check=True)
    else:
        shell = os.path.basename(os.environ.get("SHELL", "bash"))
        rc = os.environ.get("EC_RC_FILE") or os.path.join(HOME, ".zshrc" if shell == "zsh" else ".bashrc")
        line = f'export EFFECTCRAFT_CLI="{path}"'
        old = open(rc, encoding="utf-8").read().splitlines() if os.path.exists(rc) else []
        new = [l for l in old if not l.startswith("export EFFECTCRAFT_CLI=")] + [line]
        print(("would write to " if dry else "wrote to ") + f"{rc}: {line}")
        if not dry:
            open(rc, "w", encoding="utf-8").write("\n".join(new) + "\n")
    print(f"EFFECTCRAFT_CLI = {path} (EffectCraft {v}); open a new terminal / agent session to pick it up")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--set" in a:
        save(a[a.index("--set") + 1], "--dry-run" in a)
    elif "--all" in a:
        for v, p in find_all():
            print(f"{v:10} {p}")
    else:
        f = find_all()
        if not f:
            print("effectcraft-cli NOT FOUND. Ask the user where EffectCraft is installed (the folder with effectcraft-cli),\n"
                  "or to install it from https://github.com/storytold/effectcraft/releases, then run:\n"
                  "  python scripts/ec_cli.py --set <path to effectcraft-cli>")
            sys.exit(1)
        print(f"{f[0][1]}\nEffectCraft {f[0][0]}" + (f"  ({len(f) - 1} other cop{'y' if len(f) == 2 else 'ies'} found: --all)" if len(f) > 1 else ""))
