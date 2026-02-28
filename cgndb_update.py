import requests, json, time, re, shutil
from pathlib import Path
from datetime import datetime

BASE    = "https://geogratis.gc.ca/services/geoname/en/geonames.json"
HEADERS = {"User-Agent": "QuebecSalmonApp/1.0 (conservation project)"}

def slug(name):
    s = (name or "").lower()
    for a, b in [("é","e"),("è","e"),("ê","e"),("à","a"),("â","a"),("ô","o"),
                 ("û","u"),("î","i"),("ç","c"),(" ","_"),("-","_"),("'","_"),
                 ("/","_"),("(",""),(")",""),("|","")]:
        s = s.replace(a, b)
    return re.sub(r"_+","_",s).strip("_")

def fetch(params):
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:
            print(f"    retry {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return []

def to_pool(item):
    generic = item.get("generic", {})
    return {
        "cgndb_id":    item.get("id"),
        "name":        item.get("name"),
        "lat":         item.get("latitude"),
        "lon":         item.get("longitude"),
        "location":    item.get("location"),
        "accuracy_m":  item.get("accuracy"),
        "decision":    item.get("decision"),
        "generic_code": generic.get("code") if isinstance(generic, dict) else None,
    }

# ── PASS 1: bounding box queries ──────────────────────────────
BOXES = [
    ("Gaspésie-Est",        47.8, -65.5, 49.2, -64.3),
    ("Gaspésie-Centre",     47.8, -66.5, 49.2, -65.5),
    ("Gaspésie-Ouest",      47.8, -67.5, 49.2, -66.5),
    ("Bas-Saint-Laurent",   47.5, -69.5, 48.5, -67.5),
    ("Charlevoix",          47.2, -70.8, 47.9, -69.8),
    ("Saguenay",            48.0, -71.2, 48.6, -70.0),
    ("Côte-Nord-Ouest",     48.0, -70.0, 49.6, -68.5),
    ("Côte-Nord-Est",       48.0, -68.5, 49.6, -67.0),
]

print("\n── Pass 1: Bounding box queries ──────────────────")
all_pools = {}
for label, s, w, n, e in BOXES:
    items = fetch({"bbox": f"{w},{s},{e},{n}", "concise": "RIVF", "num": 1000})
    new = 0
    for item in items:
        cid = item.get("id")
        if not cid or cid in all_pools: continue
        p = to_pool(item)
        name_lower = (p["name"] or "").lower()
        # Keep only Salmon Pools: generic code 757 OR name contains fosse/pool
        if p["generic_code"] == "757" or "fosse" in name_lower or "pool" in name_lower:
            all_pools[cid] = p
            new += 1
    print(f"  {label:<25}: {len(items):4d} features → {new} salmon pools")
    time.sleep(0.4)

# ── PASS 2: keyword searches ───────────────────────────────────
print("\n── Pass 2: Keyword searches ──────────────────────")
for kw in ["fosse", "pool"]:
    skip = 0
    while True:
        items = fetch({"q": kw, "province": "24", "concise": "RIVF",
                       "num": 1000, "skip": skip})
        if not items: break
        new = 0
        for item in items:
            cid = item.get("id")
            if cid and cid not in all_pools:
                all_pools[cid] = to_pool(item)
                new += 1
        print(f"  '{kw}' skip={skip:<5}: {len(items):4d} → {new} new")
        time.sleep(0.4)
        if len(items) < 1000: break
        skip += 1000

cgndb_pools = list(all_pools.values())
print(f"\nTotal CGNDB salmon pools found: {len(cgndb_pools)}")

# ── Load master pools.json ─────────────────────────────────────
master_data = json.loads(Path("data/pools.json").read_text(encoding="utf-8"))
master = master_data["pools"]
print(f"Master pools loaded: {len(master)}")

# ── Cross-match: name similarity + proximity ───────────────────
print("\n── Cross-matching ────────────────────────────────")

# Index master by id for fast update
by_id = {p["id"]: p for p in master}

upgraded = 0
unmatched_cgndb = []

for cp in cgndb_pools:
    if not cp["lat"] or not cp["lon"]: continue
    cname = slug(cp["name"] or "")
    best_score, best_id = 0, None

    for pid, mp in by_id.items():
        mname = slug(mp.get("name") or "")
        mfull = slug(mp.get("full_name") or "")

        # Name match score
        score = 0
        if cname and cname == mname:                           score = 100
        elif cname and (cname in mfull or mname in cname):    score = 75
        elif cname:
            words = [w for w in cname.split("_") if len(w) > 3]
            if words and any(w in mfull for w in words):      score = 45

        # Proximity boost — must be within ~10km
        if score > 0 and mp.get("lat") and mp.get("lon"):
            dlat = abs(cp["lat"] - mp["lat"])
            dlon = abs(cp["lon"] - mp["lon"])
            if dlat < 0.09 and dlon < 0.09:   score += 30   # ~10km
            elif dlat < 0.18 and dlon < 0.18: score += 10   # ~20km
            else:                              score = 0     # too far, reject

        if score > best_score:
            best_score = score
            best_id = pid

    if best_score >= 75 and best_id:
        old = by_id[best_id]
        by_id[best_id] = {
            **old,
            "lat":              cp["lat"],
            "lon":              cp["lon"],
            "coord_source":     "CGNDB (NRCan official)",
            "coord_accuracy_m": cp["accuracy_m"],
            "cgndb_id":         cp["cgndb_id"],
        }
        upgraded += 1
    else:
        unmatched_cgndb.append(cp)

print(f"  Upgraded with CGNDB coordinates: {upgraded}")
print(f"  CGNDB pools not matched (new/unknown): {len(unmatched_cgndb)}")

# ── Save updated pools.json ────────────────────────────────────
# Backup first
backup = f"data/pools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
shutil.copy("data/pools.json", backup)
print(f"\n  Backup saved → {backup}")

master_data["pools"] = list(by_id.values())
master_data["count"] = len(master_data["pools"])
master_data["coord_sources"] = {
    "estimated": "Interpolated from FQSA PDF maps (±100-300m)",
    "cgndb":     "NRCan CGNDB official — Open Government Licence Canada (~100m)",
}
master_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

Path("data/pools.json").write_text(
    json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  data/pools.json updated — {len(master_data['pools'])} pools")

# Save unmatched for reference (not added automatically)
Path("cgndb_unmatched.json").write_text(
    json.dumps({"note": "CGNDB pools not matched to master — review manually",
                "count": len(unmatched_cgndb), "pools": unmatched_cgndb},
               ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  cgndb_unmatched.json saved ({len(unmatched_cgndb)} pools to review)")

# Print summary by river
print("\n── Upgraded pools by river ───────────────────────")
by_river = {}
for p in by_id.values():
    if p.get("coord_source") == "CGNDB (NRCan official)":
        r = p.get("river","Unknown")
        by_river[r] = by_river.get(r,0) + 1
for river, count in sorted(by_river.items(), key=lambda x: -x[1]):
    print(f"  {river:<40}: {count} pools upgraded")

print(f"\n✅ Done! {upgraded} pools now have official NRCan coordinates.")
