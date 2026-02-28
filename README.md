# 🎣 Quebec Atlantic Salmon Database

Open dataset of Atlantic salmon fishing pools, river flows, water temperatures and recommended flies for **24 rivers in Quebec**.

Built from FQSA / Saumon Québec official maps. Maintained as a static JSON API via jsDelivr CDN.

---

## 📁 Files

| File | Description | Records |
|------|-------------|---------|
| `data/pools.json` | All salmon pools with GPS coordinates | 1354 pools |
| `data/rivers.json` | River metadata, CEHQ flow stations, temperatures | 24 rivers |
| `data/flies.json` | Recommended flies by river and condition | 24 rivers |
| `index.json` | Master index — start here | — |

---

## 🌐 Live CDN URLs (jsDelivr)

Replace `YOUR_USERNAME` with your GitHub username:

```
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/quebec-salmon-data@main/index.json
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/quebec-salmon-data@main/data/pools.json
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/quebec-salmon-data@main/data/rivers.json
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/quebec-salmon-data@main/data/flies.json
```

---

## 🧩 Using in Lovable (or any React app)

```js
const BASE = "https://cdn.jsdelivr.net/gh/YOUR_USERNAME/quebec-salmon-data@main/";

// Fetch all pools
const res = await fetch(BASE + "data/pools.json");
const { pools } = await res.json();

// Filter by river
const bonaventurePools = pools.filter(p => p.river_slug === "riviere_bonaventure");

// Fetch river info (flows + temperatures)
const rivRes = await fetch(BASE + "data/rivers.json");
const { rivers } = await rivRes.json();
const bonaventure = rivers.find(r => r.id === "riviere_bonaventure");
console.log(bonaventure.flow_optimal_salmon_m3s); // → 10
console.log(bonaventure.temp_july_avg_c);          // → 16.2
```

---

## 🗺️ Rivers covered

| River | Region | Pools |
|-------|--------|-------|
| Grande Cascapédia | Gaspésie | 77 |
| Grande-Rivière | Gaspésie | 43 |
| Rivière à Mars | Saguenay–Lac-Saint-Jean | 93 |
| Rivière Bonaventure | Gaspésie | 96 |
| Rivière Cap-Chat | Gaspésie | 53 |
| Rivière Causapscal | Gaspésie | 25 |
| Rivière Dartmouth | Gaspésie | 37 |
| Rivière des Escoumins | Côte-Nord | 57 |
| Rivière Godbout | Côte-Nord | 37 |
| Rivière du Gouffre | Charlevoix | 64 |
| Rivière Grand Pabos | Gaspésie | 30 |
| Rivière Madeleine | Gaspésie | 76 |
| Rivière Malbaie | Charlevoix | 67 |
| Rivière Matapédia | Gaspésie / Bas-Saint-Laurent | 106 |
| Rivière Mitis | Bas-Saint-Laurent | 33 |
| Rivière Nouvelle | Gaspésie | 57 |
| Rivière Patapédia | Gaspésie / Bas-Saint-Laurent | 55 |
| Rivière Petit Pabos | Gaspésie | 54 |
| Rivière Petit-Saguenay | Saguenay–Lac-Saint-Jean | 24 |
| Rivière Rimouski | Bas-Saint-Laurent | 50 |
| Rivière Saint-Jean (Gaspé) | Gaspésie | 22 |
| Rivière Saint-Jean (Saguenay) | Saguenay–Lac-Saint-Jean | 42 |
| Rivière Sainte-Marguerite | Côte-Nord / Saguenay–Lac-Saint-Jean | 106 |
| Rivière York | Gaspésie | 50 |

---

## ⚠️ Coordinate accuracy

GPS coordinates are **estimated** (±100–300 m) from non-georeferenced PDF maps.  
For survey-grade precision, georeferenced Avenza Maps versions are needed.

---

## 📊 Data sources

- **Pools & river maps**: Fédération québécoise pour le saumon atlantique (FQSA) / Saumon Québec
- **Flows**: Centre d'expertise hydrique du Québec (CEHQ / MELCCFP)
- **Temperatures**: MELCCFP réseau de suivi thermique / ZECs / published studies
- **Flies**: FQSA / ZECs / local guides / published fly fishing literature

---

## 🤝 Contributing

Fly data `local_notes` fields are designed for crowdsourcing.  
Open a PR or issue to contribute local knowledge.

