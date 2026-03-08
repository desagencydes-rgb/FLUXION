"""
FLUXION Live Bridge API — FastAPI service integrating real-world data sources
(Overpass, Geoapify) with the validated algorithmic engine.

Provides:
  - GET  /live/waste-baskets    Fetch waste baskets from OSM Overpass
  - GET  /live/pois             Fetch restaurants/pharmacies from Geoapify
  - POST /live/gps-snap         Snap GPS coords to nearest graph vertex
  - POST /live/ingest-network   Build a GrapheRoutier from live Overpass data
  - GET  /live/health           Health check
"""
import os
import sys

# Ensure project root is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from live_bridge.overpass_client import (
    fetch_waste_baskets, fetch_recycling_centers,
    fetch_fuel_stations, osm_nodes_to_points
)
from live_bridge.geoapify_client import (
    fetch_pois, fetch_all_priority_pois, pois_to_points
)
from live_bridge.gps_snapper import snap_to_graph, snap_multiple
from live_bridge.rbac import RBACMiddleware

from niveau1.src.graphe_routier import GrapheRoutier
from niveau1.src.point_collecte import PointCollecte

# ── App Setup ──────────────────────────────────────────────────────────

app = FastAPI(
    title="FLUXION Live Bridge API",
    description="Real-world data integration layer for the FLUXION waste collection system.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RBAC enforcement
app.add_middleware(RBACMiddleware)

# ── Global State ───────────────────────────────────────────────────────

# The live graph built from Overpass data (shared across requests)
live_graphe: Optional[GrapheRoutier] = None


# ── Pydantic Models ───────────────────────────────────────────────────

class GPSCoord(BaseModel):
    lat: float
    lon: float

class GPSSnapRequest(BaseModel):
    coordinates: List[GPSCoord]

class GPSSnapResult(BaseModel):
    vertex_id: int
    distance_km: float
    lat: float
    lon: float

class PointResponse(BaseModel):
    id: int
    x: float
    y: float
    nom: str
    lat: Optional[float] = None
    lon: Optional[float] = None

class IngestResult(BaseModel):
    num_vertices: int
    num_edges: int
    sources: List[str]


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/live/health")
async def health_check():
    """Health check — returns API status and whether a live graph is loaded."""
    return {
        "status": "ok",
        "live_graph_loaded": live_graphe is not None,
        "live_graph_vertices": len(live_graphe.sommets) if live_graphe else 0
    }


@app.get("/live/waste-baskets", response_model=List[PointResponse])
async def get_waste_baskets(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius: int = Query(1000, description="Search radius in meters", ge=100, le=5000)
):
    """
    Fetches waste_basket nodes from OpenStreetMap Overpass API
    and returns them as PointCollecte objects.
    """
    nodes = fetch_waste_baskets(lat, lon, radius)
    points = osm_nodes_to_points(nodes, id_offset=1000)
    return [
        PointResponse(id=p.id, x=p.x, y=p.y, nom=p.nom, lat=p.lat, lon=p.lon)
        for p in points
    ]


@app.get("/live/pois", response_model=List[dict])
async def get_pois(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius: int = Query(1000, description="Search radius in meters", ge=100, le=5000),
    category: Optional[str] = Query(None, description="Category: restaurant, pharmacy, hotel, supermarket")
):
    """
    Fetches business POIs from Geoapify Places API.
    Without a category, fetches all priority types (restaurant, pharmacy, hotel).
    """
    if category:
        pois = fetch_pois(category, lat, lon, radius)
    else:
        pois = fetch_all_priority_pois(lat, lon, radius)

    return pois


@app.post("/live/gps-snap", response_model=List[GPSSnapResult])
async def gps_snap(request: GPSSnapRequest):
    """
    Snaps GPS coordinates to the nearest vertices in the live GrapheRoutier.
    Requires a live graph to be ingested first via /live/ingest-network.
    """
    global live_graphe
    if live_graphe is None or not live_graphe.sommets:
        raise HTTPException(
            status_code=400,
            detail="No live graph loaded. Call POST /live/ingest-network first."
        )

    coords = [{"lat": c.lat, "lon": c.lon} for c in request.coordinates]
    results = snap_multiple(coords, live_graphe)
    return [GPSSnapResult(**r) for r in results]


@app.post("/live/ingest-network", response_model=IngestResult)
async def ingest_network(
    lat: float = Query(..., description="Center latitude"),
    lon: float = Query(..., description="Center longitude"),
    radius: int = Query(1500, description="Search radius in meters", ge=500, le=10000)
):
    """
    Builds a live GrapheRoutier from real-world Overpass data.
    Fetches waste baskets + recycling centers + fuel stations,
    converts them to PointCollecte, and creates a fully-connected graph.
    """
    global live_graphe

    sources_used = []

    # Fetch from multiple sources
    waste_nodes = fetch_waste_baskets(lat, lon, radius)
    sources_used.append(f"waste_basket ({len(waste_nodes)} nodes)")

    recycling_nodes = fetch_recycling_centers(lat, lon, radius)
    sources_used.append(f"recycling ({len(recycling_nodes)} nodes)")

    fuel_nodes = fetch_fuel_stations(lat, lon, radius)
    sources_used.append(f"fuel ({len(fuel_nodes)} nodes)")

    # Convert to PointCollecte
    waste_points = osm_nodes_to_points(waste_nodes, id_offset=1000)
    recycling_points = osm_nodes_to_points(recycling_nodes, id_offset=2000)
    fuel_points = osm_nodes_to_points(fuel_nodes, id_offset=3000)

    all_points = waste_points + recycling_points + fuel_points

    if not all_points:
        raise HTTPException(
            status_code=404,
            detail="No nodes found in the specified area. Try a larger radius or different location."
        )

    # Build graph
    graphe = GrapheRoutier()

    # Add depot at center
    depot = PointCollecte(0, lon, lat, "Depot-Live", lat=lat, lon=lon)
    graphe.ajouter_sommet(depot)

    for p in all_points:
        graphe.ajouter_sommet(p)

    # Connect all pairs (full mesh for VRP)
    ids = list(graphe.sommets.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            graphe.ajouter_arete(ids[i], ids[j])

    live_graphe = graphe

    return IngestResult(
        num_vertices=len(graphe.sommets),
        num_edges=len(graphe.aretes) // 2,  # Bidirectional
        sources=sources_used
    )


# ── API Contract Summary (for frontend reference) ─────────────────────

API_CONTRACTS = {
    "GET /live/health": {
        "auth": "none",
        "response": {"status": "str", "live_graph_loaded": "bool", "live_graph_vertices": "int"}
    },
    "GET /live/waste-baskets": {
        "auth": "fleet_manager+",
        "params": {"lat": "float", "lon": "float", "radius": "int (100-5000)"},
        "response": "[{id, x, y, nom, lat, lon}]"
    },
    "GET /live/pois": {
        "auth": "fleet_manager+",
        "params": {"lat": "float", "lon": "float", "radius": "int", "category": "str?"},
        "response": "[{place_id, name, lat, lon, category, priority, address}]"
    },
    "POST /live/gps-snap": {
        "auth": "driver+",
        "body": {"coordinates": [{"lat": "float", "lon": "float"}]},
        "response": "[{vertex_id, distance_km, lat, lon}]"
    },
    "POST /live/ingest-network": {
        "auth": "fleet_manager+",
        "params": {"lat": "float", "lon": "float", "radius": "int (500-10000)"},
        "response": {"num_vertices": "int", "num_edges": "int", "sources": "[str]"}
    }
}


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("LIVE_BRIDGE_PORT", "8001"))
    uvicorn.run("live_bridge.api_bridge:app", host="0.0.0.0", port=port, reload=True)
