"""Search Wikimedia Commons (no API key) for images or video you may reuse, with licence and author for each hit.
Downloads only what you name, into its own folder, with a licence file beside it.

  python stock.py search "rainy street at night" [--video] [--limit 10]
  python stock.py get FILE_TITLE OUT_DIR          e.g. "File:Rain on window.jpg"
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "effectcraft-editor-skill/0.3 (stock search)"}
try:   # some Python installs ship a stale default CA store; certifi's bundle still verifies the certificate
    import ssl

    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = None


def fetch(url, timeout):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=CTX)


def query(params):
    with fetch(API + "?" + urllib.parse.urlencode({**params, "format": "json"}), 30) as r:
        return json.load(r)


def strip(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def info(titles):
    pages = query({"action": "query", "titles": "|".join(titles), "prop": "imageinfo",
                   "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1920})["query"]["pages"]
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
        out.append({"title": p["title"], "url": ii.get("url"), "size": f"{ii.get('width')}x{ii.get('height')}", "mime": ii.get("mime"),
                    "licence": strip(md.get("LicenseShortName", {}).get("value")), "author": strip(md.get("Artist", {}).get("value"))[:80],
                    "credit_required": md.get("AttributionRequired", {}).get("value") == "true"})
    return out


def search(q, video=False, limit=10):
    term = q + (" filetype:video" if video else " filetype:bitmap")
    hits = query({"action": "query", "list": "search", "srsearch": term, "srnamespace": 6, "srlimit": limit})["query"]["search"]
    return info([h["title"] for h in hits]) if hits else []


def get(title, out):
    meta = info([title])[0]
    if not meta["url"]:
        sys.exit(f"no file for {title}")
    os.makedirs(out, exist_ok=True)
    name = os.path.join(out, re.sub(r"[^\w.\-]+", "_", title.split(":", 1)[-1]))
    with fetch(meta["url"], 120) as r, open(name, "wb") as f:
        f.write(r.read())
    with open(name + ".licence.txt", "w", encoding="utf-8") as f:
        f.write(f"{meta['title']}\nlicence: {meta['licence']}\nauthor: {meta['author']}\nsource: {meta['url']}\n"
                f"credit required: {meta['credit_required']}\n")
    print(name); print(name + ".licence.txt")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "search":
        lim = int(a[a.index("--limit") + 1]) if "--limit" in a else 10
        for h in search(a[1], "--video" in a, lim):
            print(f"{h['title']}\n   {h['size']} {h['mime']}  licence: {h['licence'] or '?'}  by {h['author'] or '?'}")
    elif len(a) == 3 and a[0] == "get":
        get(a[1], a[2])
    else:
        sys.exit(__doc__)
