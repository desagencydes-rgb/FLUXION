# FLUXION — Agent Reference Document

> **Purpose:** This file is the single source of truth for any AI agent working on this project. Read it fully before making any changes.

---

## 1. Project Identity

- **Name:** FLUXION (evolution of "Ville Propre")
- **Goal:** SaaS waste collection optimizer for municipalities
- **Budget:** $0 — open-source only, free-tier APIs
- **Stack:** FastAPI/Python (backend) · Next.js/TypeScript (frontend) · PostgreSQL (database)

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     FLUXION ARCHITECTURE                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Next.js Dashboard]  ←──HTTP/WS──→  [FastAPI: api.py]      │
│   Port 3000                            Port 8000             │
│   ├── / (Fleet Manager)                ├── /api/state        │
│   ├── /driver (Driver)                 ├── /api/simulation/* │
│   └── /admin (NOT BUILT)               ├── /api/config       │
│                                        ├── /api/events/*     │
│  [Next.js Dashboard]  ←──HTTP──→  [FastAPI: api_bridge.py]   │
│                                    Port 8001                 │
│                                    ├── /live/waste-baskets   │
│                                    ├── /live/pois            │
│                                    ├── /live/gps-snap        │
│                                    └── /live/ingest-network  │
│                                                              │
│  [Algorithm Engine]                [Shared Utilities]         │
│   niveau1/ — Dijkstra              commun/constantes.py      │
│   niveau2/ — Bipartite             commun/database.py (SQLite)│
│   niveau3/ — Tripartite            commun/schema.sql (PG)    │
│   niveau4/ — VRP (2-opt+Tabu)      commun/validateurs.py     │
│   niveau5/ — NSGA-II               commun/geo_utils.py       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
FLUXION/
├── commun/                    # Shared Python utilities
│   ├── constantes.py          # Global constants (speeds, thresholds, limits)
│   ├── database.py            # SQLite persistence (events, zone states)
│   ├── schema.sql             # PostgreSQL schema (NOT connected yet)
│   ├── geo_utils.py           # Coordinate conversion helpers
│   ├── outils_math.py         # Math utilities
│   ├── parseur_json.py        # JSON data file parser
│   └── validateurs.py         # Input validators
│
├── niveau1/                   # Level 1: Road Network
│   ├── src/
│   │   ├── graphe_routier.py  # Graph G=(V,E), Dijkstra, distance matrix
│   │   ├── point_collecte.py  # Collection point model
│   │   └── main_niveau1.py    # Level 1 entry point
│   ├── data/                  # JSON data files
│   └── tests/test_niveau1.py  # ✅ Tests exist
│
├── niveau2/                   # Level 2: Fleet Assignment
│   ├── src/
│   │   ├── affectateur_biparti.py  # Bipartite matching
│   │   ├── camion.py          # Truck model
│   │   ├── zone.py            # Zone model
│   │   └── main_niveau2.py
│   ├── data/
│   └── tests/                 # ❌ No test files
│
├── niveau3/                   # Level 3: Temporal Planning
│   ├── src/
│   │   ├── planificateur_triparti.py  # Tripartite graph planner
│   │   ├── creneau_horaire.py # Time-slot model
│   │   ├── contrainte_temporelle.py   # Night bans, breaks, traffic
│   │   └── main_niveau3.py
│   ├── data/
│   └── tests/                 # ❌ No test files
│
├── niveau4/                   # Level 4: VRP Optimization
│   ├── src/
│   │   ├── optimiseur_vrp.py  # 2-opt + Tabu Search
│   │   ├── tournee.py         # Route/tour model
│   │   ├── visualiseur.py     # Route visualizer
│   │   ├── visualiseur_tournees.py
│   │   └── main_niveau4.py
│   ├── data/
│   └── tests/                 # ❌ No test files
│
├── niveau5/                   # Level 5: Dynamic Brain
│   ├── src/
│   │   ├── optimiseur_mo.py   # NSGA-II multi-objective optimizer
│   │   ├── simulation.py      # Real-time IoT simulator
│   │   ├── api.py             # FastAPI server (port 8000) ← MAIN API
│   │   ├── dashboard.py       # Legacy Plotly dashboard (unused)
│   │   └── main_niveau5.py
│   ├── data/
│   └── tests/test_niveau5.py  # ✅ Tests exist
│
├── live_bridge/               # Real-world data integration
│   ├── api_bridge.py          # FastAPI server (port 8001)
│   ├── overpass_client.py     # OSM Overpass API client
│   ├── geoapify_client.py     # Geoapify Places API client
│   ├── gps_snapper.py         # GPS → graph vertex snapping
│   ├── rbac.py                # RBAC middleware (NOT mounted on bridge)
│   └── tests/test_live_bridge.py  # ✅ Tests exist
│
├── dashboard/                 # Next.js 16 frontend
│   ├── app/
│   │   ├── page.tsx           # Fleet Manager dashboard
│   │   ├── driver/page.tsx    # Driver companion (mobile-first)
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Tailwind + custom styles
│   ├── components/
│   │   ├── map/FluxionMap.tsx          # Leaflet map (satellite toggle)
│   │   ├── analytics/SavingsWidget.tsx # ROI tickers + sparkline
│   │   ├── controls/WeightSliders.tsx  # NSGA-II weight sliders
│   │   ├── controls/IncidentSimulator.tsx  # Truck breakdown trigger
│   │   ├── driver/DutyToggle.tsx       # On/off duty toggle
│   │   └── driver/TourneeChecklist.tsx # Route checklist
│   ├── hooks/
│   │   ├── useSimulation.ts   # Polls /api/state
│   │   └── useSavings.ts      # Polls /api/savings (ENDPOINT MISSING)
│   ├── lib/api.ts             # API client (ports 8000 + 8001)
│   ├── types/fluxion.ts       # TypeScript interfaces
│   └── package.json           # Dependencies (React 19, Leaflet, Chart.js)
│
├── PROJECT_MANIFEST_FLUXION.txt  # Original project blueprint
├── projetFM.pdf               # Academic specification (French)
└── pdf_text.txt               # Extracted text from PDF
```

---

## 4. Key Constants (from `commun/constantes.py`)

| Constant | Value | Meaning |
|----------|-------|---------|
| `VITESSE_MOYENNE_KMH` | 30 | Average truck speed |
| `CONSOMMATION_L_PAR_KM` | 0.35 | Fuel consumption |
| `CO2_KG_PAR_LITRE` | 2.68 | CO₂ per liter diesel |
| `SEUIL_URGENCE` | 90% | Bin fill → urgent |
| `SEUIL_CRITIQUE` | 95% | Bin fill → critical |
| `HEURE_DEBUT_INTERDIT_NUIT` | 22 | Night collection ban start |
| `HEURE_FIN_INTERDIT_NUIT` | 6 | Night collection ban end |
| `DELAI_MAX_REPLANIFICATION_S` | 120 | Max 2min replanning |
| `SEUIL_DESEQUILIBRE_MAX_PCT` | 20% | Max load imbalance |

---

## 5. RBAC Roles

| Role | Access |
|------|--------|
| `super_admin` | Everything |
| `fleet_manager` | Dashboard, weights, config, event triggers, live data |
| `driver` | Read-only state, GPS snap, simulation controls |

**Current implementation:** Header-based (`X-User-Role`). Must be upgraded to JWT.

---

## 6. API Endpoints

### Simulation API (`api.py` — port 8000)
| Method | Path | Role | Status |
|--------|------|------|--------|
| GET | `/api/state` | driver | ✅ |
| POST | `/api/simulation/step` | driver | ✅ |
| POST | `/api/simulation/play` | driver | ✅ |
| POST | `/api/simulation/pause` | driver | ✅ |
| POST | `/api/simulation/weights` | fleet_manager | ✅ |
| GET | `/api/config` | fleet_manager | ✅ |
| POST | `/api/config` | fleet_manager | ✅ |
| POST | `/api/events/trigger` | fleet_manager | ✅ |
| GET | `/api/savings` | driver | ❌ **MISSING** |
| WS | `/ws/` | driver | ✅ (unused by frontend) |

### Live Bridge API (`api_bridge.py` — port 8001)
| Method | Path | Role | Status |
|--------|------|------|--------|
| GET | `/live/health` | open | ✅ |
| GET | `/live/waste-baskets` | fleet_manager | ✅ |
| GET | `/live/pois` | fleet_manager | ✅ |
| POST | `/live/gps-snap` | driver | ✅ |
| POST | `/live/ingest-network` | fleet_manager | ✅ |

---

## 7. PostgreSQL Schema Tables (from `schema.sql`)

- `organizations` — multi-tenant orgs
- `users` — email/password/role per org
- `camions` — fleet per org (plate, capacity, cost)
- `points_collecte` — collection points with GPS + override coords
- `savings_logs` — daily ROI metrics (naive vs optimized distance, money, CO₂, fuel)

---

## 8. Running the Project

```bash
# Backend (simulation)
cd FLUXION
python -m niveau5.src.api        # Starts on port 8000

# Backend (live bridge)
python -m live_bridge.api_bridge # Starts on port 8001

# Frontend
cd dashboard
npm run dev                      # Starts on port 3000
```

## 9. External APIs Used

| API | Purpose | Auth |
|-----|---------|------|
| Overpass (OSM) | Waste baskets, recycling, fuel stations | None (free) |
| Geoapify Places | Restaurants, pharmacies, hotels | API key in env |
| Traccar Client | Live GPS from driver phones | **NOT IMPLEMENTED** |
| Esri World Imagery | Satellite map tiles | Free tier |
