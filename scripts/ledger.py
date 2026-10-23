"""Append-only run ledger (ledger.jsonl beside the project): what ran, on which inputs, what it produced, with SHA-256.
After a crash or timeout, read the ledger before re-running anything: a step that wrote its outputs is done; a step
with a start but no end is UNKNOWN - inspect its outputs, don't replay an edit blindly.

  python ledger.py start STEP [--inputs F ...]          -> prints a run id
  python ledger.py end RUN_ID [--outputs F ...] [--status ok|failed] [--note TEXT]
  python ledger.py status [--ledger PATH]               last state of every step; unfinished runs flagged
  python ledger.py verify [--ledger PATH]               re-hash recorded outputs; flags files changed since
Library: from ledger import Ledger; with Ledger().step("render", inputs=[...]) as s: ...; s.outputs += [...]
"""
import hashlib
import json
import os
import sys
import time
import uuid

DEFAULT = os.environ.get("EC_LEDGER", "ledger.jsonl")


def sha(path):
    if os.path.isdir(path):
        h = hashlib.sha256()
        for root, _, files in sorted(os.walk(path)):
            for f in sorted(files):
                h.update(f.encode()); h.update(sha(os.path.join(root, f)).encode())
        return h.hexdigest()
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Ledger:
    def __init__(self, path=DEFAULT):
        self.path = path

    def write(self, rec):
        rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def start(self, step, inputs=()):
        rid = uuid.uuid4().hex[:10]
        self.write({"run": rid, "event": "start", "step": step, "inputs": {p: sha(p) for p in inputs}})
        return rid

    def end(self, rid, outputs=(), status="ok", note=""):
        self.write({"run": rid, "event": "end", "status": status, "note": note, "outputs": {p: sha(p) for p in outputs}})

    def records(self):
        if not os.path.exists(self.path):
            return []
        return [json.loads(l) for l in open(self.path, encoding="utf-8") if l.strip()]

    def step(self, name, inputs=()):
        led = self

        class Ctx:
            outputs = []

            def __enter__(self):
                self.rid = led.start(name, inputs); return self

            def __exit__(self, et, ev, tb):
                led.end(self.rid, self.outputs, "failed" if et else "ok", str(ev) if ev else ""); return False
        return Ctx()

    def status(self):
        runs = {}
        for r in self.records():
            runs.setdefault(r["run"], {}).update(r)
        last = {}
        for rid, r in runs.items():
            last[r.get("step", "?")] = (rid, r)
        lines = []
        for step, (rid, r) in last.items():
            state = r.get("status") or "UNKNOWN (started, never ended: inspect outputs before re-running)"
            lines.append(f"{step:14} {rid}  {state}  {r.get('at', '')}  {len(r.get('outputs', {}))} outputs")
        return lines

    def verify(self):
        bad = []
        for r in self.records():
            for p, h in (r.get("outputs") or {}).items():
                now = sha(p)
                if h and now != h:
                    bad.append(f"{p}: {'missing' if now is None else 'changed'} since run {r['run']}")
        return bad


if __name__ == "__main__":
    a = sys.argv[1:]
    path = DEFAULT
    if "--ledger" in a:
        i = a.index("--ledger"); path = a[i + 1]; del a[i:i + 2]
    L = Ledger(path)

    def listopt(k):
        if k not in a:
            return []
        i = a.index(k); vals = []
        for v in a[i + 1:]:
            if v.startswith("--"):
                break
            vals.append(v)
        return vals
    if not a:
        sys.exit(__doc__)
    if a[0] == "start":
        print(L.start(a[1], listopt("--inputs")))
    elif a[0] == "end":
        st = a[a.index("--status") + 1] if "--status" in a else "ok"
        note = a[a.index("--note") + 1] if "--note" in a else ""
        L.end(a[1], listopt("--outputs"), st, note)
    elif a[0] == "status":
        print("\n".join(L.status()) or "empty ledger")
    elif a[0] == "verify":
        bad = L.verify(); print("\n".join(bad) or "all recorded outputs unchanged"); sys.exit(1 if bad else 0)
    else:
        sys.exit(__doc__)
