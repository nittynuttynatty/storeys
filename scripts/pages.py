"""Build one small page per project (p/<slug>/) so shared links get a proper
title and preview in WhatsApp/Telegram, then hop into the app on that project.
Runs in the publish workflow; the pages are not committed."""
import json, os, re, html, datetime, sys
sys.path.insert(0, os.path.dirname(__file__))
try:
    from cards import card
except Exception as e:  # Pillow missing: pages still build, just without picture previews
    print("no preview cards:", e); card = None

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = "TOP Already?"
cname = os.path.join(ROOT, "CNAME")
SITE = ("https://" + open(cname).read().strip() + "/") if os.path.exists(cname) else "https://topalready.github.io/"

def slug(s):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))

def ym(s):
    if not s:
        return None
    y, m = s.split("-")[:2]
    return datetime.date(int(y), int(m), 1)

def fmt(d):
    return d.strftime("%b %Y") if d else "not announced"

today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date()
d = json.load(open(os.path.join(ROOT, "data.json")))
rows = [("BTO", r[0], r[2], r[3], r[4]) for r in d["bto"]] + [("Condo", r[0], r[1], r[2], "") for r in d["condo"]]

made = 0
for kind, name, launch, ecd, delayed in rows:
    s = slug(name)
    L, T = ym(launch), ym(delayed or ecd)
    pct = None
    if L and T and T > L:
        pct = max(0, min(100, round((today - L).days / (T - L).days * 100)))
        desc = f"{pct}% of the wait to keys is over. Expected {'completion' if kind == 'BTO' else 'TOP'}: {fmt(T)}. See site photos from people nearby."
    else:
        desc = f"Expected {'completion' if kind == 'BTO' else 'TOP'}: {fmt(T)}. See site photos from people nearby."
    title = f"{name} ({kind}) · {APP}"
    url = f"{SITE}p/{s}/"
    e = html.escape
    os.makedirs(os.path.join(ROOT, "p", s), exist_ok=True)
    img = f"{SITE}icon-512.png"
    if card:
        try:
            card(os.path.join(ROOT, "p", s, "card.png"), name, kind, pct, f"Expected {'completion' if kind == 'BTO' else 'TOP'}: {fmt(T)}")
            img = f"{url}card.png"
        except Exception as e:
            print("card failed", name, e)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{APP}">
<meta property="og:title" content="{e(name)}: how far along is it?">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0;url=../../?p={s}">
<link rel="icon" href="../../icon-192.png">
<style>body{{font:16px/1.5 system-ui,sans-serif;background:#F6EFE2;color:#3A2C26;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center;padding:16px}}</style>
</head><body><p>Opening <a href="../../?p={s}">{e(name)} on {APP}</a>…</p>
<script>location.replace("../../?p={s}")</script></body></html>"""
    os.makedirs(os.path.join(ROOT, "p", s), exist_ok=True)
    open(os.path.join(ROOT, "p", s, "index.html"), "w").write(page)
    made += 1
print("project pages", made, "for", SITE)
