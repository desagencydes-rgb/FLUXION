"""
FLUXION Simulation API — v2.0
Full-featured: truck movement, duty management, zone collection,
CSV/Excel import, multi-type points, VRP at scale, real metrics.
"""
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Request
import httpx
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import sys
import io
import math
import random
import logging
from typing import List, Optional, Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau5.src.simulation import SimulateurTempsReel
from niveau1.src.point_collecte import PointCollecte
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from commun.parseur_json import charger_json
from commun.constantes import CONSOMMATION_L_PAR_KM, CO2_KG_PAR_LITRE, PRIX_CARBURANT_EUR
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")

# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="FLUXION Waste Collection Optimization API v2")

try:
    from live_bridge.auth import auth_router
    app.include_router(auth_router)
except ImportError:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Remove duplicate imports that were moved up


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    path = request.url.path
    if (path.startswith("/docs") or path.startswith("/openapi")
            or path.startswith("/ws") or path.startswith("/auth")):
        return await call_next(request)
    expected_key = os.getenv("API_KEY", "")
    if expected_key and expected_key not in ("dev-key-changeme-in-production", "change-me", ""):
        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != expected_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


# ── Point Type Taxonomy ────────────────────────────────────────────────────────

POINT_TYPE_ICONS = {
    "trash_bin":   "🗑️",
    "hotel":       "🏨",
    "restaurant":  "🍽️",
    "pharmacy":    "💊",
    "hospital":    "🏥",
    "industrial":  "🏭",
    "commercial":  "🏪",
    "school":      "🏫",
    "office":      "🏢",
    "market":      "🛒",
    "generic":     "📍",
    "depot":       "📦",
    "refuel":      "⛽",
    "wash":        "🚿",
}

# ── Global Simulation State ───────────────────────────────────────────────────

simulation_instance: Optional[SimulateurTempsReel] = None
is_playing = False
simulation_step_count = 0

# Depot and special points
DEPOT = {"id": 0, "lat": 33.5731, "lon": -7.5898, "name": "Main Depot", "type": "depot"}
REFUEL_POINTS = [
    {"id": "r1", "lat": 33.5850, "lon": -7.6100, "name": "Station Total", "type": "refuel"},
    {"id": "r2", "lat": 33.5620, "lon": -7.5700, "name": "Station Shell", "type": "refuel"},
]

# Truck state registry: positions, duty, load
truck_registry: Dict[int, Dict[str, Any]] = {}

# Zone collection tracking
zone_collection: Dict[int, Dict[str, Any]] = {}  # zone_id -> {collected, collected_by, collected_at}

# Duty persistence
duty_state: Dict[int, bool] = {}  # camion_id -> on_duty bool

# Routes / ROI state
current_routes = {
    "naive_distance": 0.0,
    "optimized_distance": 0.0,
    "optimized_paths": [],
    "naive_paths": [],
    "total_fuel_consumed_l": 0.0,
    "total_money_consumed": 0.0,
    "time_elapsed_min": 0,
}

# Customizable weights
current_weights = {"distance": 0.7, "time": 0.2, "co2": 0.1}
depot_coords = {"x": 0.0, "y": 0.0, "lat": DEPOT["lat"], "lon": DEPOT["lon"]}
active_simulation_level = 5

# WebSocket clients
connected_clients: List[WebSocket] = []

# Previous zones for delta computation
_prev_zones_snapshot: Dict[int, float] = {}


# ── Simulation Initialization ─────────────────────────────────────────────────

def _make_realistic_lat_lon(index: int, base_lat=33.5731, base_lon=-7.5898, spread=0.08) -> tuple:
    """Generate realistic scattered coordinates around a city center."""
    angle = (index * 137.5) % 360  # golden angle for good spread
    radius = spread * math.sqrt((index % 15 + 1) / 15)
    lat = base_lat + radius * math.cos(math.radians(angle))
    lon = base_lon + radius * math.sin(math.radians(angle))
    return round(lat, 6), round(lon, 6)


def init_simulation():
    global simulation_instance, truck_registry, zone_collection, duty_state
    import csv

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(base_dir) # This should point to c:\Projects\FLUXION
    
    points_csv = os.path.join(root_dir, "points_morocco.csv")
    trucks_csv = os.path.join(root_dir, "trucks_morocco.csv")
    input2_path = os.path.join(root_dir, "niveau2", "data", "input_niveau2.json")

    zones = []
    camions = []

    if os.path.exists(points_csv) and os.path.exists(trucks_csv):
        with open(points_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                z_id = int(row["id"])
                lat, lon = float(row["lat"]), float(row["lon"])
                vol = float(row["volume_l"])
                z = Zone(z_id, [], vol, lon * 100, lat * 100)
                z.centre = (lon * 100, lat * 100)
                z.point_type = row["type"]
                z.nom = row["name"]
                z.city = row.get("city", "Casablanca")
                zones.append(z)
                
        with open(trucks_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                c_id = int(row["id"])
                c = Camion(c_id, float(row["capacity_l"]), 150)
                c.type = row["type"]
                c.speed_kmh = float(row["speed_kmh"])
                c.start_lat = float(row["lat"])
                c.start_lon = float(row["lon"])
                c.city = row.get("city", "Casablanca")
                camions.append(c)
        logger.info(f"Loaded {len(zones)} zones, {len(camions)} trucks from Morocco CSVs")
    else:
        try:
            data2 = charger_json(input2_path)
            zones = [Zone.from_dict(z) for z in data2["zones"]]
            camions = [Camion.from_dict(c) for c in data2["camions"]]
            logger.info(f"Loaded {len(zones)} zones, {len(camions)} trucks from JSON config")
        except (FileNotFoundError, Exception):
            # Default demo setup: 12 zones, 3 trucks
            zones = []
            for i in range(1, 13):
                lat, lon = _make_realistic_lat_lon(i)
                z = Zone(i, [], 50 + random.randint(0, 200), lat * 100, lon * 100)
                z.centre = (lat * 100, lon * 100)
                zones.append(z)

            camions = [
                Camion(1, 5000, 150),
                Camion(2, 8000, 200),
                Camion(3, 3000, 100),
            ]
            logger.info("Using default demo: 12 zones, 3 trucks")

    simulation_instance = SimulateurTempsReel(zones, camions)

    # Pre-seed zones to 50-85% fill so routing + savings are non-zero immediately
    for z in simulation_instance.zones:
        capteur = simulation_instance.capteurs_zones.get(z.id)
        if capteur:
            capteur.valeur = random.uniform(50, 85)

    # Initialize truck registry with realistic positions
    truck_registry.clear()
    zone_collection.clear()
    duty_state.clear()
    for i, c in enumerate(simulation_instance.camions):
        lat = getattr(c, "start_lat", DEPOT["lat"] + i * 0.001)
        lon = getattr(c, "start_lon", DEPOT["lon"] + i * 0.001)
        truck_registry[c.id] = {
            "lat": lat,
            "lon": lon,
            "target_lat": lat,
            "target_lon": lon,
            "progress": 0.0,
            "current_zone_target": None,
            "route_queue": [],      # list of (lat, lon) waypoints
            "route_index": 0,
            "on_duty": False,
            "speed_kmh": 40,
            "type": getattr(c, "type", "standard"),
            "allowed_types": getattr(c, "allowed_types", list(POINT_TYPE_ICONS.keys())),
            "city": getattr(c, "city", "Casablanca"),
        }
        duty_state[c.id] = False

    logger.info("Simulation engine initialized.")


def init_truck_routes():
    """After recalculate_routes, assign waypoints to truck_registry for animation."""
    global truck_registry
    if not current_routes.get("optimized_paths"):
        return
    for path_info in current_routes["optimized_paths"]:
        cid = path_info.get("camion_id")
        path = path_info.get("points", [])
        if cid in truck_registry and path:
            waypoints = []
            for p in path:
                # Convert x/y (scaled lat/lon * 100) back to lat/lon
                waypoints.append((p["y"] / 100 if abs(p["y"]) > 90 else p["y"],
                                   p["x"] / 100 if abs(p["x"]) > 180 else p["x"]))
            truck_registry[cid]["route_queue"] = waypoints
            truck_registry[cid]["route_index"] = 0
            if waypoints:
                truck_registry[cid]["target_lat"] = waypoints[0][0]
                truck_registry[cid]["target_lon"] = waypoints[0][1]


init_simulation()


# ── VRP / Routing ─────────────────────────────────────────────────────────────

class MockGrapheRoutier:
    """Mock graph to compute distances dynamically using haversine for massive scale."""
    def __init__(self, lat=None, lon=None):
        dep_lat = lat if lat else DEPOT["lat"]
        dep_lon = lon if lon else DEPOT["lon"]
        self.points = {0: PointCollecte(0, dep_lon * 100, dep_lat * 100, "Depot")}
        self.aretes = {}

    def recuperer_point(self, id_pt):
        if id_pt in self.points:
            return self.points[id_pt]
        if id_pt == 0:
            return self.points[0]
        # Resolve dynamically
        if simulation_instance:
            z = next((z for z in simulation_instance.zones if z.id == id_pt), None)
            if z:
                cx, cy = z.centre
                plat, plon = coord_to_latlon(cx, cy)
                pt = PointCollecte(id_pt, plon * 100, plat * 100, f"Zone {id_pt}")
                self.points[id_pt] = pt
                return pt
        return PointCollecte(id_pt, 0, 0, "Unknown")

    def calcul_distance(self, p1_id, p2_id):
        p1 = self.recuperer_point(p1_id)
        p2 = self.recuperer_point(p2_id)
        if not p1 or not p2:
            return 9999.0
        # Extrapolate back to lat/lon
        lat1, lon1 = p1.y / 100.0, p1.x / 100.0
        lat2, lon2 = p2.y / 100.0, p2.x / 100.0
        return _haversine_km(lat1, lon1, lat2, lon2)

    def matrice_distances(self, subset_ids=None):
        """Returns distance matrix for the VRP optimizer."""
        # Calculate dynamic matrix only for the given subset to avoid O(N^2) on the whole country
        p_ids = list(subset_ids) if subset_ids else list(self.points.keys())
        matrix = {p: {} for p in p_ids}
        for i in p_ids:
            for j in p_ids:
                if i == j:
                    matrix[i][j] = 0.0
                else:
                    lat_i, lon_i = self.points[i].y / 100, self.points[i].x / 100
                    lat_j, lon_j = self.points[j].y / 100, self.points[j].x / 100
                    matrix[i][j] = _haversine_km(lat_i, lon_i, lat_j, lon_j)
        return matrix


def _kmeans_cluster(points: List[Dict], n_clusters: int) -> List[List[int]]:
    """Simple k-means clustering for points to handle scale. Returns list of lists of point IDs."""
    if len(points) <= n_clusters:
        return [[p["id"]] for p in points]

    try:
        from sklearn.cluster import KMeans
        import numpy as np
        coords = np.array([[p["lat"], p["lon"]] for p in points])
        km = KMeans(n_clusters=min(n_clusters, len(points)), random_state=42, n_init=10)
        labels = km.fit_predict(coords)
        clusters: Dict[int, List[int]] = {}
        for pid, label in zip([p["id"] for p in points], labels):
            clusters.setdefault(int(label), []).append(pid)
        return list(clusters.values())
    except Exception:
        # Fallback: split evenly
        ids = [p["id"] for p in points]
        chunk = max(1, len(ids) // n_clusters)
        return [ids[i:i+chunk] for i in range(0, len(ids), chunk)]


def recalculate_routes():
    global current_routes
    if not simulation_instance:
        return

    camions_en_panne = {evt.get("camion_id") for evt in simulation_instance.evenements
                        if evt.get("type") == "PANNE_CAMION"}
    camions_actifs = [c for c in simulation_instance.camions if c.id not in camions_en_panne]
    if not camions_actifs:
        camions_actifs = simulation_instance.camions[:]

    # Build point list for zones > 50% fill
    zones_to_route = []
    zone_city_map = {}

    for z in simulation_instance.zones:
        capteur = simulation_instance.capteurs_zones.get(z.id)
        if capteur and capteur.valeur > 50:
            # Convert centre coords -> lat/lon 
            cx, cy = z.centre
            lat, lon = coord_to_latlon(cx, cy)
            city_name = getattr(z, "city", "Casablanca")
            pt = {"id": z.id, "lat": lat, "lon": lon, "fill": capteur.valeur, "city": city_name}
            zones_to_route.append(pt)
            zone_city_map.setdefault(city_name, []).append(pt)

    if not zones_to_route:
        return

    # Group trucks by city
    truck_city_map = {}
    for c in camions_actifs:
        city_name = truck_registry.get(c.id, {}).get("city", "Casablanca")
        truck_city_map.setdefault(city_name, []).append(c)

    opt_tours = []
    naive_dist = 0.0
    opt_dist = 0.0

    # Optimize each city independently
    for city, city_zones in zone_city_map.items():
        city_trucks = truck_city_map.get(city, [])
        if not city_trucks:
            continue

        # Build local dict_points for this city
        t_lat = truck_registry.get(city_trucks[0].id, {}).get("lat", DEPOT["lat"])
        t_lon = truck_registry.get(city_trucks[0].id, {}).get("lon", DEPOT["lon"])
        graphe = MockGrapheRoutier(t_lat, t_lon)
        
        city_dict_points = {0: graphe.points[0]}
        for z in city_zones:
            # Make sure graphe has them cached
            city_dict_points[z["id"]] = graphe.recuperer_point(z["id"])

        # Decide iteration scale
        TABU_ITER = max(5, min(30, 2000 // len(city_zones)))

        if len(city_zones) > 100:
            # Cluster-first approach to avoid long wait times
            clusters = _kmeans_cluster(city_zones, len(city_trucks))
            for i, cluster_ids in enumerate(clusters):
                if i >= len(city_trucks):
                    break
                t_id = city_trucks[i].id
                camion = city_trucks[i]
                
                # Build subset dict_points for this truck
                sub_dict = {0: graphe.points[0]}
                for pid in cluster_ids:
                    if pid in city_dict_points:
                        sub_dict[pid] = city_dict_points[pid]
                
                try:
                    opt = OptimiseurVRP(graphe, [camion], sub_dict)
                    naive_tours = opt.construire_solution_initiale()
                    d_n = sum(t.calculer_distance(graphe) for t in naive_tours)
                    tournees = opt.recherche_tabou(iterations=TABU_ITER)
                    
                    naive_dist += d_n
                    for t in tournees:
                        t._cached_distance = t.calculer_distance(graphe)
                        opt_tours.append(t)
                        opt_dist += t._cached_distance
                except Exception as e:
                    logger.error(f"VRP Error in clustering for {city} truck {t_id}: {e}")
        else:
            # Small dataset: assign altogether
            try:
                opt = OptimiseurVRP(graphe, city_trucks, city_dict_points)
                naive_tours = opt.construire_solution_initiale()
                naive_dist += sum(t.calculer_distance(graphe) for t in naive_tours)
                
                tournees = opt.recherche_tabou(iterations=TABU_ITER)
                for t in tournees:
                    t._cached_distance = t.calculer_distance(graphe)
                    opt_tours.append(t)
                    opt_dist += t._cached_distance
            except Exception as e:
                logger.error(f"VRP Error for {city}: {e}")

    distance_saved = max(0.0, naive_dist - opt_dist)
    # Update elapsed metrics
    steps = simulation_step_count
    fuel_consumed = opt_dist * CONSOMMATION_L_PAR_KM
    money_consumed = fuel_consumed * PRIX_CARBURANT_EUR
    distance_saved = max(0.0, naive_dist - opt_dist)
    fuel_saved = distance_saved * CONSOMMATION_L_PAR_KM
    co2_saved = fuel_saved * CO2_KG_PAR_LITRE
    money_saved = fuel_saved * PRIX_CARBURANT_EUR

    opt_paths_coord = []
    for t in opt_tours:
        path = []
        cid = t.camion_id
        c_lat = truck_registry.get(cid, {}).get("lat", DEPOT["lat"])
        c_lon = truck_registry.get(cid, {}).get("lon", DEPOT["lon"])
        
        for pid in t.points_ids:
            if pid == 0:
                path.append({"x": c_lon * 100, "y": c_lat * 100, "id": 0, "type": "depot"})
            else:
                z = next((z for z in simulation_instance.zones if z.id == pid), None)
                if z:
                    path.append({"x": z.centre[0], "y": z.centre[1], "id": z.id, "type": getattr(z, "type", "trash_bin")})
        opt_paths_coord.append({"camion_id": cid, "points": path,
                                 "distance_km": round(getattr(t, "_cached_distance", 0.0), 2)})

    current_routes.update({
        "naive_distance": round(naive_dist, 2),
        "optimized_distance": round(opt_dist, 2),
        "optimized_paths": opt_paths_coord,
        "total_fuel_consumed_l": round(fuel_consumed, 2),
        "total_money_consumed": round(money_consumed, 2),
        "time_elapsed_min": steps * 15,
        "_savings": {
            "distance_saved_km": round(distance_saved, 2),
            "fuel_saved_l": round(fuel_saved, 2),
            "co2_reduced_kg": round(co2_saved, 2),
            "money_saved": round(money_saved, 2),
        }
    })

    # Update truck waypoints for animation
    for path_info in opt_paths_coord:
        cid = path_info["camion_id"]
        if cid in truck_registry:
            waypoints = []
            for p in path_info["points"]:
                # Convert x/y back to lat/lon
                lat_v = p["y"] / 100 if abs(p["y"]) > 90 else p["y"]
                lon_v = p["x"] / 100 if abs(p["x"]) > 180 else p["x"]
                waypoints.append((lat_v, lon_v))
            truck_registry[cid]["route_queue"] = waypoints
            truck_registry[cid]["route_index"] = 0


# ── Universal Coordinate Converter ───────────────────────────────────────────

# Casablanca city center (for grid-km offset system)
_CITY_LAT = 33.5731
_CITY_LON = -7.5898
_KM_PER_DEG_LAT = 111.0
_KM_PER_DEG_LON = 91.0  # ≈ 111 * cos(33.5°)


def coord_to_latlon(cx: float, cy: float):
    """
    Universal converter for all coordinate systems used in this project:
      - lat*100 / lon*100  → abs(cy) > 90  → divide by 100
      - real lat/lon       → 10 < abs(cy) < 90  → use as-is
      - grid-km (x/y in km offset from city center) → abs values < 50
    Returns (lat, lon) as real WGS84 degrees.
    """
    # System 1: lat*100 / lon*100 (e.g. cy=3357.3 → lat=33.573)
    if abs(cy) > 90:
        lat = cy / 100.0
        lon = cx / 100.0
        return lat, lon

    # System 2: real lat/lon already (e.g. cy=33.57, cx=-7.59)
    if abs(cy) > 10 and abs(cx) > 0.5:
        return float(cy), float(cx)

    # System 3: tiny grid-km offset (e.g. x=5.2, y=3.0)
    # Treat as km north/east offset from city center
    lat = _CITY_LAT + cy / _KM_PER_DEG_LAT
    lon = _CITY_LON + cx / _KM_PER_DEG_LON
    return lat, lon


# ── State Serialization ───────────────────────────────────────────────────────

def build_state_response() -> Dict:
    if not simulation_instance:
        raise HTTPException(status_code=500, detail="Simulation not initialized")

    zones_data = []
    for z in simulation_instance.zones:
        capteur = simulation_instance.capteurs_zones.get(z.id)
        fill = capteur.valeur if capteur else 0
        cx, cy = z.centre
        lat, lon = coord_to_latlon(cx, cy)
        coll = zone_collection.get(z.id, {})
        zones_data.append({
            "id": z.id,
            "x": cx, "y": cy,
            "lat": lat, "lon": lon,
            "volume_estime": z.volume_estime,
            "fill_level": fill,
            "type": getattr(z, "point_type", "trash_bin"),
            "name": getattr(z, "nom", f"Zone {z.id}"),
            "city": getattr(z, "city", "Casablanca"),
            "collected": coll.get("collected", False),
            "collected_by": coll.get("collected_by"),
        })

    camions_data = []
    for c in simulation_instance.camions:
        tr = truck_registry.get(c.id, {})
        camions_data.append({
            "id": c.id,
            "capacite": c.capacite,
            "charge_actuelle": c.charge_actuelle,
            "lat": tr.get("lat", DEPOT["lat"]),
            "lon": tr.get("lon", DEPOT["lon"]),
            "on_duty": duty_state.get(c.id, False),
            "type": tr.get("type", "standard"),
            "city": tr.get("city", "Casablanca"),
        })

    # Routes as proper Route array
    routes = []
    for path_info in current_routes.get("optimized_paths", []):
        routes.append({
            "camion_id": path_info["camion_id"],
            "points": path_info["points"],
            "distance_km": path_info.get("distance_km", 0),
        })

    return {
        "status": "running" if is_playing else "paused",
        "zones": zones_data,
        "camions": camions_data,
        "recent_events": simulation_instance.evenements[-20:],
        "routes": routes,
        "depot": DEPOT,
        "refuel_points": REFUEL_POINTS,
        "metrics": {
            "naive_distance_km": current_routes["naive_distance"],
            "optimized_distance_km": current_routes["optimized_distance"],
            "distance_saved_km": current_routes.get("_savings", {}).get("distance_saved_km", 0),
            "fuel_saved_l": current_routes.get("_savings", {}).get("fuel_saved_l", 0),
            "co2_reduced_kg": current_routes.get("_savings", {}).get("co2_reduced_kg", 0),
            "money_saved": current_routes.get("_savings", {}).get("money_saved", 0),
            "fuel_consumed_l": current_routes["total_fuel_consumed_l"],
            "money_consumed": current_routes["total_money_consumed"],
            "time_elapsed_min": current_routes["time_elapsed_min"],
        }
    }


# ── Simulation Loop ───────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _advance_trucks(dt_seconds: float = 2.0):
    """Move each on-duty truck toward its next waypoint."""
    for cid, tr in truck_registry.items():
        if not duty_state.get(cid, False):
            continue
        queue = tr.get("route_queue", [])
        idx = tr.get("route_index", 0)
        if not queue or idx >= len(queue):
            continue

        target_lat, target_lon = queue[idx]
        dist_km = _haversine_km(tr["lat"], tr["lon"], target_lat, target_lon)
        speed_kms = tr.get("speed_kmh", 40) / 3600  # km per second
        move_km = speed_kms * dt_seconds * 60  # simulate at 60x speed for demo

        if move_km >= dist_km:
            # Arrived at waypoint
            tr["lat"] = target_lat
            tr["lon"] = target_lon
            tr["route_index"] = idx + 1
            tr["progress"] = 0.0
        else:
            # Interpolate toward target
            frac = move_km / max(dist_km, 0.0001)
            tr["lat"] += frac * (target_lat - tr["lat"])
            tr["lon"] += frac * (target_lon - tr["lon"])
            tr["progress"] = frac


async def background_simulation_loop():
    global is_playing, simulation_step_count
    TICK = 2.0  # seconds between ticks

    while True:
        await asyncio.sleep(TICK)
        if not is_playing or not simulation_instance:
            continue

        # Advance simulation
        events = simulation_instance.executer_pas_de_temps(15)
        simulation_step_count += 1

        # Advance truck positions
        _advance_trucks(TICK)

        # Recalculate routes periodically (every 5 steps to reduce CPU)
        if simulation_step_count % 5 == 0:
            recalculate_routes()

        if not connected_clients:
            continue

        # Compute delta: only changed zones
        changed_zones = []
        for z in simulation_instance.zones:
            capteur = simulation_instance.capteurs_zones.get(z.id)
            fill = capteur.valeur if capteur else 0.0
            prev = _prev_zones_snapshot.get(z.id, -1)
            if abs(fill - prev) > 0.5:  # only if changed by >0.5%
                cx, cy = z.centre
                lat, lon = coord_to_latlon(cx, cy)
                changed_zones.append({
                    "id": z.id, "fill_level": fill,
                    "lat": lat, "lon": lon,
                    "collected": zone_collection.get(z.id, {}).get("collected", False),
                })
                _prev_zones_snapshot[z.id] = fill

        # Truck positions for the dashboard map
        truck_positions = [
            {"id": cid, "lat": tr["lat"], "lon": tr["lon"], "on_duty": duty_state.get(cid, False)}
            for cid, tr in truck_registry.items()
        ]

        payload = {
            "type": "SIMULATION_UPDATE",
            "events": events,
            "zones": changed_zones,  # delta only
            "truck_positions": truck_positions,
            "metrics": current_routes.get("_savings", {}),
            "routes": build_state_response()["routes"],
        }

        dead = []
        for client in connected_clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead.append(client)
        for d in dead:
            connected_clients.remove(d)


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/state")
async def get_state():
    return build_state_response()


@app.get("/api/savings")
async def get_savings():
    s = current_routes.get("_savings", {})
    return {
        "money_saved": s.get("money_saved", 0),
        "fuel_saved_l": s.get("fuel_saved_l", 0),
        "co2_reduced_kg": s.get("co2_reduced_kg", 0),
        "distance_saved_km": s.get("distance_saved_km", 0),
        "fuel_consumed_l": current_routes.get("total_fuel_consumed_l", 0),
        "money_consumed": current_routes.get("total_money_consumed", 0),
        "time_elapsed_min": current_routes.get("time_elapsed_min", 0),
    }


@app.post("/api/simulation/step")
async def step_simulation():
    global simulation_step_count
    if not simulation_instance:
        raise HTTPException(status_code=500, detail="Simulation not initialized")
    events = simulation_instance.executer_pas_de_temps(15)
    simulation_step_count += 1
    _advance_trucks(2.0)
    recalculate_routes()
    return {"message": "Step executed", "events": events, "metrics": current_routes.get("_savings", {})}


@app.post("/api/simulation/play")
async def play_simulation():
    global is_playing
    is_playing = True
    return {"message": "Simulation playing", "status": "running"}


@app.post("/api/simulation/pause")
async def pause_simulation():
    global is_playing
    is_playing = False
    return {"message": "Simulation paused", "status": "paused"}


@app.post("/api/simulation/reset")
async def reset_simulation():
    global is_playing, simulation_step_count
    is_playing = False
    simulation_step_count = 0
    init_simulation()
    recalculate_routes()
    return {"message": "Simulation reset"}


# ── Driver Duty Endpoints ─────────────────────────────────────────────────────

class DutyPayload(BaseModel):
    camion_id: int
    on_duty: bool


@app.get("/api/driver/duty")
async def get_duty(camion_id: int):
    return {"camion_id": camion_id, "on_duty": duty_state.get(camion_id, False)}


@app.post("/api/driver/duty")
async def set_duty(payload: DutyPayload):
    duty_state[payload.camion_id] = payload.on_duty
    if payload.camion_id in truck_registry:
        truck_registry[payload.camion_id]["on_duty"] = payload.on_duty
        if payload.on_duty:
            # When going on duty, trigger a route recalculation
            global is_playing
            is_playing = True
            recalculate_routes()
    logger.info(f"Truck {payload.camion_id} duty → {'ON' if payload.on_duty else 'OFF'}")
    return {"camion_id": payload.camion_id, "on_duty": payload.on_duty}


# ── Zone Collection Endpoint ───────────────────────────────────────────────────

class CollectPayload(BaseModel):
    camion_id: int
    zone_id: int


@app.post("/api/driver/collect")
async def collect_zone(payload: CollectPayload):
    """Driver marks a zone as collected. Enforces truck capacity."""
    if not simulation_instance:
        raise HTTPException(status_code=500, detail="Simulation not initialized")

    zone = next((z for z in simulation_instance.zones if z.id == payload.zone_id), None)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {payload.zone_id} not found")

    camion = next((c for c in simulation_instance.camions if c.id == payload.camion_id), None)
    if not camion:
        raise HTTPException(status_code=404, detail=f"Truck {payload.camion_id} not found")

    if not duty_state.get(payload.camion_id, False):
        raise HTTPException(status_code=400, detail="Truck must be on duty to collect")

    if zone_collection.get(payload.zone_id, {}).get("collected"):
        raise HTTPException(status_code=409, detail="Zone already collected")

    # Capacity check
    capteur = simulation_instance.capteurs_zones.get(zone.id)
    volume_to_collect = zone.volume_estime * (capteur.valeur / 100.0) if capteur else zone.volume_estime
    remaining_capacity = camion.capacite - camion.charge_actuelle

    if volume_to_collect > remaining_capacity:
        raise HTTPException(
            status_code=422,
            detail=f"Truck capacity exceeded: need {volume_to_collect:.0f}L, only {remaining_capacity:.0f}L free"
        )

    # Execute collection
    camion.charge_actuelle += volume_to_collect
    if capteur:
        capteur.valeur = 0.0  # Zone emptied

    from datetime import datetime
    zone_collection[payload.zone_id] = {
        "collected": True,
        "collected_by": payload.camion_id,
        "collected_at": datetime.utcnow().isoformat(),
        "volume_collected": volume_to_collect,
    }

    simulation_instance.evenements.append({
        "type": "ZONE_COLLECTED",
        "zone_id": payload.zone_id,
        "camion_id": payload.camion_id,
        "volume": round(volume_to_collect, 1),
        "message": f"Truck {payload.camion_id} collected Zone {payload.zone_id} ({volume_to_collect:.0f}L)"
    })

    recalculate_routes()
    logger.info(f"Zone {payload.zone_id} collected by truck {payload.camion_id} ({volume_to_collect:.0f}L)")
    return {
        "success": True,
        "zone_id": payload.zone_id,
        "camion_id": payload.camion_id,
        "volume_collected": round(volume_to_collect, 1),
        "truck_load": round(camion.charge_actuelle, 1),
        "truck_capacity": camion.capacite,
    }


@app.post("/api/driver/unload")
async def unload_truck(camion_id: int):
    """Driver arrives at depot and unloads."""
    camion = next((c for c in simulation_instance.camions if c.id == camion_id), None)
    if not camion:
        raise HTTPException(status_code=404, detail=f"Truck {camion_id} not found")
    unloaded = camion.charge_actuelle
    camion.charge_actuelle = 0.0
    return {"success": True, "unloaded_l": round(unloaded, 1)}


# ── Configuration Endpoints ────────────────────────────────────────────────────

class NodePayload(BaseModel):
    id: int
    x: float
    y: float
    volume: float
    type: str = "trash_bin"
    name: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None


class TruckPayload(BaseModel):
    id: int
    capacite: float
    cout_fixe: float
    type: str = "standard"
    speed_kmh: float = 40.0
    allowed_types: List[str] = []


class ConfigPayload(BaseModel):
    level: int
    zones: List[NodePayload]
    depot: NodePayload
    camions: List[TruckPayload]


@app.get("/api/config")
async def get_config():
    if not simulation_instance:
        raise HTTPException(status_code=500, detail="Simulation not initialized")
    zones = []
    for z in simulation_instance.zones:
        cx, cy = z.centre
        zones.append({
            "id": z.id, "x": cx, "y": cy,
            "volume": z.volume_estime,
            "type": getattr(z, "point_type", "trash_bin"),
            "name": getattr(z, "nom", f"Zone {z.id}"),
        })
    camions = []
    for c in simulation_instance.camions:
        tr = truck_registry.get(c.id, {})
        camions.append({
            "id": c.id, "capacite": c.capacite, "cout_fixe": getattr(c, "cout_fixe", 0),
            "type": tr.get("type", "standard"), "speed_kmh": tr.get("speed_kmh", 40),
        })
    return {
        "level": active_simulation_level,
        "depot": {"id": 0, "x": depot_coords["x"], "y": depot_coords["y"],
                  "lat": DEPOT["lat"], "lon": DEPOT["lon"], "volume": 0},
        "zones": zones, "camions": camions,
    }


@app.post("/api/config")
async def set_config(payload: ConfigPayload):
    global simulation_instance, active_simulation_level, is_playing, depot_coords

    if payload.level < 1 or payload.level > 5:
        raise HTTPException(status_code=400, detail="level must be 1-5")

    is_playing = False
    active_simulation_level = payload.level
    depot_coords["x"] = payload.depot.x
    depot_coords["y"] = payload.depot.y
    if payload.depot.lat:
        depot_coords["lat"] = payload.depot.lat
        DEPOT["lat"] = payload.depot.lat
    if payload.depot.lon:
        depot_coords["lon"] = payload.depot.lon
        DEPOT["lon"] = payload.depot.lon

    zones = []
    for zp in payload.zones:
        z = Zone(zp.id, [], zp.volume, zp.x, zp.y)
        z.point_type = zp.type
        z.nom = zp.name or f"Zone {zp.id}"
        z.city = "Casablanca" # Standard UI config defaults to Casa
        zones.append(z)

    camions = []
    for cp in payload.camions:
        c = Camion(cp.id, cp.capacite, cp.cout_fixe)
        camions.append(c)
        truck_registry[cp.id] = {
            "lat": DEPOT["lat"], "lon": DEPOT["lon"],
            "target_lat": DEPOT["lat"], "target_lon": DEPOT["lon"],
            "progress": 0.0, "route_queue": [], "route_index": 0,
            "on_duty": duty_state.get(cp.id, False),
            "speed_kmh": cp.speed_kmh, "type": cp.type,
            "allowed_types": cp.allowed_types,
            "city": "Casablanca"
        }

    simulation_instance = SimulateurTempsReel(zones, camions)
    for z in simulation_instance.zones:
        capteur = simulation_instance.capteurs_zones.get(z.id)
        if capteur:
            capteur.valeur = random.uniform(50, 85)

    recalculate_routes()
    return {"message": "Configuration updated", "zones": len(zones), "camions": len(camions)}


# ── CSV / Excel Import ─────────────────────────────────────────────────────────

POINT_COLUMNS_REQUIRED = {"id", "lat", "lon"}
TRUCK_COLUMNS_REQUIRED = {"id", "capacity_l"}


def _parse_dataframe(content: bytes, filename: str):
    """Parse CSV or Excel into pandas DataFrame."""
    import pandas as pd
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content), engine="openpyxl")
    else:
        # Try comma, semicolon, tab
        for sep in [",", ";", "\t"]:
            df = pd.read_csv(io.BytesIO(content), sep=sep)
            if len(df.columns) > 1:
                return df
        return pd.read_csv(io.BytesIO(content))


@app.post("/api/import/points")
async def import_collection_points(file: UploadFile = File(...)):
    """
    Import collection points from CSV or Excel.
    Required columns: id, lat, lon
    Optional: name, type, volume_l, priority, open_hour, close_hour
    """
    global simulation_instance, zone_collection

    if not file.filename or not (file.filename.endswith((".csv", ".xlsx", ".xls"))):
        raise HTTPException(status_code=400, detail="File must be .csv or .xlsx")

    content = await file.read()
    try:
        df = _parse_dataframe(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = POINT_COLUMNS_REQUIRED - set(df.columns)
    if missing:
        raise HTTPException(status_code=422,
                            detail=f"Missing required columns: {missing}. Got: {list(df.columns)}")

    errors = []
    zones = []
    for i, row in df.iterrows():
        try:
            row_id = int(row["id"])
            lat = float(row["lat"])
            lon = float(row["lon"])
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                errors.append(f"Row {i+2}: Invalid coordinates ({lat}, {lon})")
                continue
            volume = float(row.get("volume_l", 50))
            z = Zone(row_id, [], volume, lon * 100, lat * 100)
            z.centre = (lon * 100, lat * 100)
            z.point_type = str(row.get("type", "trash_bin")).lower()
            z.nom = str(row.get("name", f"Point {row_id}"))
            z.city = str(row.get("_city", "Casablanca"))
            zones.append(z)
        except Exception as e:
            errors.append(f"Row {i+2}: {e}")

    if not zones:
        raise HTTPException(status_code=422, detail=f"No valid rows imported. Errors: {errors}")

    # Replace simulation zones
    existing_camions = simulation_instance.camions[:] if simulation_instance else [Camion(1, 5000, 150)]
    simulation_instance = SimulateurTempsReel(zones, existing_camions)
    for z in simulation_instance.zones:
        capteur = simulation_instance.capteurs_zones.get(z.id)
        if capteur:
            capteur.valeur = random.uniform(50, 85)
    zone_collection.clear()
    recalculate_routes()

    return {
        "success": True,
        "imported_points": len(zones),
        "errors": errors,
        "error_count": len(errors),
    }


@app.post("/api/import/trucks")
async def import_trucks(file: UploadFile = File(...)):
    """
    Import trucks from CSV or Excel.
    Required columns: id, capacity_l
    Optional: name, type, speed_kmh, cost_per_km, allowed_types
    """
    global simulation_instance

    if not file.filename or not (file.filename.endswith((".csv", ".xlsx", ".xls"))):
        raise HTTPException(status_code=400, detail="File must be .csv or .xlsx")

    content = await file.read()
    try:
        df = _parse_dataframe(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = TRUCK_COLUMNS_REQUIRED - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {missing}")

    errors = []
    camions = []
    for i, row in df.iterrows():
        try:
            cid = int(row["id"])
            capacite = float(row["capacity_l"])
            cout_fixe = float(row.get("cost_per_km", 2.5))
            c = Camion(cid, capacite, cout_fixe)
            speed = float(row.get("speed_kmh", 40))
            truck_type = str(row.get("type", "standard")).lower()
            allowed = [t.strip() for t in str(row.get("allowed_types", "")).split(",") if t.strip()]
            t_city = str(row.get("_city", "Casablanca"))
            # Spawn the truck at the city's rough coordinates, rather than all in Casa
            t_lat = float(row.get("lat", DEPOT["lat"]))
            t_lon = float(row.get("lon", DEPOT["lon"]))
            
            truck_registry[cid] = {
                "lat": t_lat, "lon": t_lon,
                "target_lat": t_lat, "target_lon": t_lon,
                "progress": 0.0, "route_queue": [], "route_index": 0,
                "on_duty": False, "speed_kmh": speed, "type": truck_type,
                "allowed_types": allowed or list(POINT_TYPE_ICONS.keys()),
                "city": t_city
            }
            duty_state[cid] = False
            camions.append(c)
        except Exception as e:
            errors.append(f"Row {i+2}: {e}")

    if not camions:
        raise HTTPException(status_code=422, detail=f"No valid trucks imported. Errors: {errors}")

    existing_zones = simulation_instance.zones[:] if simulation_instance else []
    simulation_instance = SimulateurTempsReel(existing_zones, camions)
    recalculate_routes()

    return {"success": True, "imported_trucks": len(camions), "errors": errors}


# ── Events ────────────────────────────────────────────────────────────────────

class EventPayload(BaseModel):
    type: str
    details: Dict[str, Any] = {}


@app.post("/api/events/trigger")
async def trigger_event(payload: EventPayload):
    if not simulation_instance:
        raise HTTPException(status_code=500, detail="Simulation not initialized")
    event_type = payload.type.lower()
    target_id = payload.details.get("target_id", 1)
    new_event = None
    if event_type == "panne_camion":
        new_event = {"type": "PANNE_CAMION", "camion_id": target_id, "message": "Truck breakdown"}
    elif event_type == "trafic_intense":
        new_event = {"type": "TRAFIC_INTENSE", "zone_id": target_id, "message": "Heavy traffic"}
    elif event_type == "urgence":
        new_event = {"type": "URGENCE", "zone_id": target_id, "message": "Emergency collection needed"}
    if not new_event:
        raise HTTPException(status_code=400, detail="Unknown event type")
    simulation_instance.evenements.append(new_event)
    return {"message": "Event injected", "event": new_event}


# ── Weights ────────────────────────────────────────────────────────────────────

class WeightsPayload(BaseModel):
    distance: float
    time: float
    co2: float


@app.post("/api/simulation/weights")
async def set_weights(payload: WeightsPayload):
    global current_weights
    current_weights = {"distance": payload.distance, "time": payload.time, "co2": payload.co2}
    recalculate_routes()
    return {"message": "Weights updated", "weights": current_weights}


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    # Send initial full state immediately
    try:
        await websocket.send_json({"type": "INIT", **build_state_response()})
    except Exception:
        pass
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    try:
        from commun.database import init_db
        await init_db()
    except Exception as e:
        logger.warning(f"DB init skipped: {e}")

    # Run initial route calculation so savings are non-zero from the start
    recalculate_routes()
    asyncio.create_task(background_simulation_loop())
    logger.info("FLUXION API v2 started — all systems nominal")




# ── OSRM Road-Snapping Proxy ─────────────────────────────────────────────────

@app.get("/api/route")
async def get_road_route(coords: str):
    """
    Proxy OSRM routing to avoid browser CORS + rate-limit issues.
    coords: semicolon-separated 'lon,lat' pairs (OSRM expects lon,lat order).
    Returns: { geometry: [[lat, lon], ...] }
    """
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(osrm_url, params=params)
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError("OSRM returned no valid route")

        # OSRM GeoJSON coords are [lon, lat] — flip to [lat, lon] for Leaflet
        geojson_coords = data["routes"][0]["geometry"]["coordinates"]
        leaflet_coords = [[c[1], c[0]] for c in geojson_coords]
        return {"geometry": leaflet_coords, "source": "osrm"}

    except Exception as e:
        logger.warning(f"OSRM proxy fallback triggered: {e}")
        # Fall back: parse the raw coords and return straight-line points
        try:
            pairs = coords.split(";")
            fallback = [[float(p.split(",")[1]), float(p.split(",")[0])] for p in pairs]
        except Exception:
            fallback = []
        return {"geometry": fallback, "source": "fallback"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("niveau5.src.api:app", host="0.0.0.0", port=8000, reload=True)
