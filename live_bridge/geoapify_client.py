"""
Geoapify Places API client for fetching business POIs (restaurants, pharmacies, hotels).
Uses the free-tier API with an API key loaded from environment variable GEOAPIFY_API_KEY.
"""
import urllib.request
import json
import os
from typing import List, Dict

from niveau1.src.point_collecte import PointCollecte

GEOAPIFY_BASE_URL = "https://api.geoapify.com/v2/places"
REQUEST_TIMEOUT = 10

# Category mapping for high-priority waste generation POIs
CATEGORY_MAP = {
    "restaurant": "catering.restaurant",
    "pharmacy": "healthcare.pharmacy",
    "hotel": "accommodation.hotel",
    "supermarket": "commercial.supermarket",
}

# Priority weights: higher = more waste generated → higher collection priority
PRIORITY_WEIGHTS = {
    "restaurant": 1.5,
    "pharmacy": 0.8,
    "hotel": 1.2,
    "supermarket": 1.8,
}


def _get_api_key() -> str:
    """Reads the Geoapify API key from environment."""
    key = os.getenv("GEOAPIFY_API_KEY", "")
    if not key:
        print("[GeoapifyClient] Warning: GEOAPIFY_API_KEY not set. Requests will fail.")
    return key


def fetch_pois(category: str, lat: float, lon: float,
               radius_m: int = 1000, limit: int = 50) -> List[Dict]:
    """
    Fetches Points of Interest from Geoapify Places API.

    Args:
        category: One of 'restaurant', 'pharmacy', 'hotel', 'supermarket'.
        lat: Center latitude.
        lon: Center longitude.
        radius_m: Search radius in meters.
        limit: Max results.

    Returns:
        List of dicts with keys: place_id, name, lat, lon, category, priority.
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    geoapify_category = CATEGORY_MAP.get(category, category)

    url = (
        f"{GEOAPIFY_BASE_URL}"
        f"?categories={geoapify_category}"
        f"&filter=circle:{lon},{lat},{radius_m}"
        f"&limit={limit}"
        f"&apiKey={api_key}"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FLUXION/1.0",
                 "Accept": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"[GeoapifyClient] Network error: {e}")
        return []

    pois = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])

        pois.append({
            "place_id": props.get("place_id", ""),
            "name": props.get("name", f"POI-{len(pois)}"),
            "lat": coords[1],
            "lon": coords[0],
            "category": category,
            "priority": PRIORITY_WEIGHTS.get(category, 1.0),
            "address": props.get("formatted", "")
        })

    return pois


def fetch_all_priority_pois(lat: float, lon: float,
                            radius_m: int = 1000) -> List[Dict]:
    """
    Fetches all high-priority POI categories (restaurants, pharmacies, hotels)
    in a single call sequence.
    """
    all_pois = []
    for category in ["restaurant", "pharmacy", "hotel"]:
        pois = fetch_pois(category, lat, lon, radius_m)
        all_pois.extend(pois)
    return all_pois


def pois_to_points(pois: List[Dict],
                   id_offset: int = 2000) -> List[PointCollecte]:
    """
    Converts Geoapify POI dicts into PointCollecte instances.

    Args:
        pois: List from fetch_pois() or fetch_all_priority_pois().
        id_offset: Starting ID to avoid collisions.

    Returns:
        List of PointCollecte with GPS coordinates and priority in name.
    """
    points = []
    for i, poi in enumerate(pois):
        name = f"[{poi['category']}] {poi['name']}"
        pc = PointCollecte(
            id_point=id_offset + i,
            x=poi["lon"],
            y=poi["lat"],
            nom=name,
            lat=poi["lat"],
            lon=poi["lon"]
        )
        points.append(pc)
    return points
