"""
fetch_conditions.py
Runs twice daily via GitHub Actions.
Fetches live flow data from CEHQ for all 24 Quebec salmon rivers
and writes current conditions to Supabase.
"""

import os, re, requests, json
from datetime import datetime, timezone
from supabase import create_client

# ── Supabase client ───────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── River stations (slug, name, cehq_id, optimal_flow_m3s) ───
RIVERS = [
    ("grande_cascapedia",          "Grande Cascapédia",              "011001", 15.0),
    ("riviere_bonaventure",        "Rivière Bonaventure",            "010802", 10.0),
    ("riviere_matapedia",          "Rivière Matapédia",              "021601", 35.0),
    ("riviere_causapscal",         "Rivière Causapscal",             "021701",  6.0),
    ("riviere_cap_chat",           "Rivière Cap-Chat",               "012401",  8.0),
    ("riviere_madeleine",          "Rivière Madeleine",              "013001",  9.0),
    ("riviere_nouvelle",           "Rivière Nouvelle",               "011301",  7.0),
    ("riviere_dartmouth",          "Rivière Dartmouth",              "013201",  3.5),
    ("riviere_saint_jean_gaspe",   "Rivière Saint-Jean (Gaspé)",     "013101",  4.0),
    ("riviere_york",               "Rivière York",                   "013301",  5.5),
    ("riviere_grand_pabos",        "Rivière Grand Pabos",            "012101",  3.0),
    ("riviere_petit_pabos",        "Rivière Petit Pabos",            "012201",  1.5),
    ("riviere_grande_riviere",     "Rivière Grande-Rivière",         "012301",  2.2),
    ("riviere_patapedia",          "Rivière Patapédia",              "021801",  8.0),
    ("riviere_mitis",              "Rivière Mitis",                  "022504", 14.0),
    ("riviere_rimouski",           "Rivière Rimouski",               "022301", 12.0),
    ("riviere_du_gouffre",         "Rivière du Gouffre",             "023601",  7.0),
    ("riviere_malbaie",            "Rivière Malbaie",                "023501", 16.0),
    ("riviere_a_mars",             "Rivière à Mars",                 "061901",  5.5),
    ("riviere_petit_saguenay",     "Rivière Petit-Saguenay",         "061801",  4.5),
    ("riviere_saint_jean_saguenay","Rivière Saint-Jean (Saguenay)",  "061701",  8.0),
    ("riviere_sainte_marguerite",  "Rivière Sainte-Marguerite",      "073601", 18.0),
    ("riviere_des_escoumins",      "Rivière des Escoumins",          "073001",  9.0),
    ("riviere_godbout",            "Rivière Godbout",                "072501", 12.0),
]

CEHQ_URL = "https://www.cehq.gouv.qc.ca/suivihydro/graphique.asp?NoStation={}"
HEADERS  = {"User-Agent": "QuebecSalmonApp/1.0 (conservation project)"}

def get_condition(flow, optimal):
    """Classify current flow relative to optimal salmon migration flow."""
    if flow is None:         return "unknown"
    ratio = flow / optimal
    if ratio < 0.35:         return "low"       # 🔴 very low, fish passage difficult
    elif ratio < 0.70:       return "suboptimal" # 🟡 below ideal
    elif ratio <= 1.60:      return "optimal"    # 🟢 ideal fishing conditions
    elif ratio <= 3.00:      return "high"       # 🟡 high but fishable
    else:                    return "flood"      # 🔴 dangerous, no fishing

def fetch_flow(station_id):
    """
    Fetch current flow from CEHQ.
    CEHQ embeds the latest value in the page HTML.
    We parse the most recent data point.
    """
    try:
        url = CEHQ_URL.format(station_id)
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text

        # CEHQ embeds data as JavaScript arrays in the page
        # Pattern: latest flow value in m³/s
        patterns = [
            r'debit["\s]*:["\s]*([\d.]+)',           # JSON-style
            r'Débit[^<]*:\s*([\d.]+)\s*m',           # text label
            r'"y":\s*([\d.]+)(?:[^}]*"x")',          # chart data point
            r'val(?:eur)?["\s:]+([0-9]+\.?[0-9]*)',  # generic value
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                # Take the last match (most recent data point)
                val = float(matches[-1])
                if 0 < val < 5000:   # sanity check
                    return round(val, 2)
    except Exception as e:
        print(f"    Error fetching station {station_id}: {e}")
    return None

def fetch_level(station_id):
    """Fetch current water level (metres) from CEHQ."""
    try:
        url = CEHQ_URL.format(station_id)
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text
        patterns = [
            r'niveau["\s]*:["\s]*([\d.]+)',
            r'Niveau[^<]*:\s*([\d.]+)\s*m',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                val = float(matches[-1])
                if 0 < val < 50:
                    return round(val, 3)
    except:
        pass
    return None

# ── Main fetch loop ───────────────────────────────────────────
print(f"\n{'='*55}")
print(f"CEHQ Fetch — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print(f"{'='*55}")

rows = []
for slug, name, station_id, optimal in RIVERS:
    print(f"  {name:<40} station {station_id} ... ", end="", flush=True)

    flow  = fetch_flow(station_id)
    level = fetch_level(station_id)
    cond  = get_condition(flow, optimal)

    row = {
        "river_slug":   slug,
        "river_name":   name,
        "cehq_station": station_id,
        "flow_m3s":     flow,
        "level_m":      level,
        "condition":    cond,
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
    }
    rows.append(row)

    flow_str = f"{flow} m³/s" if flow else "N/A"
    print(f"{flow_str:<12} → {cond}")

# ── Write to Supabase ─────────────────────────────────────────
print(f"\nWriting {len(rows)} rows to Supabase...")
result = sb.table("river_conditions").insert(rows).execute()
print(f"✅ Inserted {len(result.data)} rows")

# ── Prune old rows (keep only last 7 days) ────────────────────
# This prevents the table growing indefinitely
cutoff = datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
)
from datetime import timedelta
cutoff = cutoff - timedelta(days=7)
sb.table("river_conditions") \
  .delete() \
  .lt("fetched_at", cutoff.isoformat()) \
  .execute()
print(f"🧹 Pruned rows older than 7 days")

print(f"\nDone. Next run in ~12 hours.")
