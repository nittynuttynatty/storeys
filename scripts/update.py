"""Daily refresh of Storeys data.
BTO dates + delays: BTO HQ TOP tracker. BTO blocks/postal codes: OneMap.
Condo launch + expected TOP: EdgeProp new-launch pages."""
import json, re, time, html, urllib.parse, urllib.request, datetime, os

UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36"
DATA = os.path.join(os.path.dirname(__file__), "..", "data.json")
MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def get(url, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print("fetch failed", url, e)
            time.sleep(2)
    return ""

def next_data(s):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
    return json.loads(m.group(1)) if m else None

# Sites OneMap can't find by name yet (no blocks or postal codes published)
KNOWN_SITES = {
    "Mount Pleasant Crest": [1.3297, 103.8344],  # former Old Police Academy, Thomson Road, by Mount Pleasant MRT
}

old = json.load(open(DATA))
old_bto = {r[0]: r for r in old["bto"]}
old_condo = {r[0]: r for r in old["condo"]}

# ---------- BTO ----------
raw = []
for p in range(1, 15):
    d = next_data(get(f"https://www.btohq.com/bto-top-tracker/{p}"))
    rows = (d or {}).get("props", {}).get("pageProps", {}).get("data")
    if not rows:
        break
    raw += rows
    time.sleep(0.5)
print("BTO HQ rows", len(raw))

def onemap(name):
    roads, blks, postals, ll = [], [], [], None
    q = urllib.parse.quote(name)
    for page in range(1, 7):
        s = get(f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={q}&returnGeom=Y&getAddrDetails=Y&pageNum={page}")
        try:
            j = json.loads(s)
        except Exception:
            break
        for it in j.get("results", []):
            if it["BUILDING"].upper() != name.upper():
                continue
            if it["ROAD_NAME"] not in ("NIL", "") and it["ROAD_NAME"] not in roads: roads.append(it["ROAD_NAME"])
            if it["BLK_NO"] not in ("NIL", "") and it["BLK_NO"] not in blks: blks.append(it["BLK_NO"])
            if it["POSTAL"] not in ("NIL", "") and it["POSTAL"] not in postals: postals.append(it["POSTAL"])
            if ll is None: ll = [round(float(it["LATITUDE"]), 4), round(float(it["LONGITUDE"]), 4)]
        if page >= j.get("totalNumPages", 1):
            break
        time.sleep(0.2)
    return "|".join(roads), " ".join(blks), " ".join(postals), ll

def point(name, addr=""):
    """Best-effort map point for a project: name variants, then postal code, then street."""
    base = re.sub(r"\(.*?\)", "", name).replace("’", "'").strip()
    plain = re.sub(r"\s+I\s*&\s*II", "", base)
    cands = [base, plain, plain.split("@")[0].strip(), plain.split("@")[0].strip() + " I"]
    cands += re.findall(r"\b\d{6}\b", addr)[:1]
    m = re.search(r"([A-Za-z][A-Za-z ']+(Road|Rd|Drive|Dr|Avenue|Ave|Street|St|Lane|Close|Way|Walk|Link|Central|Crescent|Rise|Green|Gardens|Grove|View|Place|Promenade|Vista|Circle|Boulevard))", addr)
    if m: cands.append(m.group(1))
    for c in cands:
        s = get("https://www.onemap.gov.sg/api/common/elastic/search?searchVal=" + urllib.parse.quote(c) + "&returnGeom=Y&getAddrDetails=N&pageNum=1")
        try:
            r = json.loads(s).get("results") or []
        except Exception:
            r = []
        if r:
            return [round(float(r[0]["LATITUDE"]), 4), round(float(r[0]["LONGITUDE"]), 4)]
        time.sleep(0.2)
    return None

bto = []
if len(raw) >= 0.7 * len(old["bto"]):
    names = [(x["PROJECT_DISPLAY_NAME"] or x["PROJECT_NAME"].replace("-", " ")).strip() for x in raw]
    for x, name in zip(raw, names):
        label = name
        if names.count(name) > 1:
            l = x["LAUNCH_DATE"][:7]
            label = f"{name} ({MONTHS[int(l[5:7])]} {l[:4]} launch)"
        prev = old_bto.get(label)
        if prev and prev[7]:
            roads, blks, postals, ll = prev[6], prev[7], prev[8], prev[9]
        else:
            roads, blks, postals, ll = onemap(name)
            if not blks and prev:
                roads, blks, postals, ll = prev[6], prev[7], prev[8], prev[9] or ll
        if not ll:
            ll = (prev[9] if prev else None) or point(name) or KNOWN_SITES.get(name)
        bto.append([label, x["PROJECT_TYPE"], x["LAUNCH_DATE"][:7], (x["ESTIMATED_TOP"] or "")[:7],
                    (x["ESTIMATED_DELAYED_TOP"] or "")[:7], x["REMARKS"] or "", roads, blks, postals, ll])
else:
    print("BTO source looks broken, keeping previous data")
    bto = old["bto"]

# ---------- Condos ----------
cand = list(old_condo.keys())
d = next_data(get("https://www.edgeprop.sg/new-launches"))
if d:
    pp = d["props"]["pageProps"]
    for k in ["MAPMARKER_NEWLAUNCHES", "MAPMARKER_PASTLAUNCHES", "latestLaunchesData", "upcomingLaunchesData"]:
        for x in pp.get(k) or []:
            n = (x.get("project_name") or x.get("title") or "").strip()
            if n and n.lower() not in [c.lower() for c in cand]:
                cand.append(n)
print("condo candidates", len(cand))

def slugs(n):
    b = n.lower().replace("’", "'").strip()
    a = re.sub(r"[^a-z0-9@&' ]", "", b)
    c = [a.replace(" ", "-"), re.sub(r"['&]", "", a).replace(" ", "-"), re.sub(r"\s*@\s*", "-", a).replace(" ", "-"),
         re.sub(r"\s+ec$", "", a).replace(" ", "-"), re.sub(r"[^a-z0-9 ]", "", b).replace(" ", "-")]
    return list(dict.fromkeys(re.sub("-+", "-", x) for x in c))

QM = {"Q1": "03", "Q2": "06", "Q3": "09", "Q4": "12"}
def mnum(s): return int(s[:4]) * 12 + int(s[5:7])
condo, seen = [], set()
for n in cand:
    if n.lower() in seen:
        continue
    seen.add(n.lower())
    got = None
    for sl in slugs(n):
        t = get("https://www.edgeprop.sg/new-launches/" + urllib.parse.quote(sl, safe="@-,"), tries=1)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
        if not m:
            continue
        t = m.group(1)
        cd = re.search(r'"completion_date":"([^"]*)"', t)
        ld = re.search(r'"launch_date_text":"([^"]*)"', t)
        sa = re.search(r'"site_address":"([^"]*)"', t)
        if cd or ld:
            got = (cd.group(1) if cd else "", ld.group(1)[:7] if ld else "", sa.group(1) if sa else "")
            break
        time.sleep(0.3)
    if not got:
        if n in old_condo: condo.append(old_condo[n])
        continue
    m = re.match(r"(Q[1-4])\s*(\d{4})", got[0])
    top = f"{m.group(2)}-{QM[m.group(1)]}" if m else ""
    launch = got[1] if re.match(r"\d{4}-\d{2}", got[1]) else ""
    if not top or top < "2026-01":
        continue
    if launch and mnum(top) - mnum(launch) < 18:
        continue
    addr = html.unescape(got[2].encode().decode("unicode_escape", "ignore") if "\\u" in got[2] else got[2]).strip()
    prev = old_condo.get(n)
    ll = (prev[4] if prev and len(prev) > 4 else None) or point(n, addr)
    condo.append([n, launch, top, addr, ll])
if len(condo) < 0.7 * len(old["condo"]):
    print("Condo source looks broken, keeping previous data")
    condo = old["condo"]

out = {"updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
       "bto": bto, "condo": condo}
json.dump(out, open(DATA, "w"), ensure_ascii=False, separators=(",", ":"))
print("saved", len(bto), "BTO,", len(condo), "condos")
