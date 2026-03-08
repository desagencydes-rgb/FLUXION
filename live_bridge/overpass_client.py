"""
Overpass API client for fetching real-world waste collection infrastructure nodes.
Queries OpenStreetMap for waste baskets, recycling centers, and fuel stations.
"""
import urllib.request
import json
from typing import List, Dict, Optional

from niveau1.src.point_collecte import PointCollecte

# Overpass API endpoint (public, no key needed)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Default timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 15


def _build_query(amenity_type: str, lat: float, lon: float, radius_m: int) -> str:
    """
    Builds an Overpass QL query to fetch nodes of a given amenity type
    within a radius around a center point.
    """
    return f"""
    [out:json][timeout:10];
    (
      node["amenity"="{amenity_type}"](around:{radius_m},{lat},{lon});
    );
    out body;
    """


def fetch_overpass_nodes(amenity_type: str, lat: float, lon: float,
                         radius_m: int = 1000) -> List[Dict]:
    """
    Fetches OSM nodes of the given amenity type from the Overpass API.

    Args:
        amenity_type: OSM amenity tag (e.g. 'waste_basket', 'recycling', 'fuel').
        lat: Center latitude.
        lon: Center longitude.
        radius_m: Search radius in meters (default 1000m).

    Returns:
        List of dicts with keys: osm_id, lat, lon, tags.
    """
    query = _build_query(amenity_type, lat, lon, radius_m)
    data = query.encode("utf-8")

    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "FLUXION/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"[OverpassClient] Network error: {e}")
        return []

    nodes = []
    for element in result.get("elements", []):
        if element.get("type") == "node":
            nodes.append({
                "osm_id": element["id"],
                "lat": element["lat"],
                "lon": element["lon"],
                "tags": element.get("tags", {})
            })
    return nodes


def fetch_waste_baskets(lat: float, lon: float,
                        radius_m: int = 1000) -> List[Dict]:
    """Fetches waste_basket nodes from Overpass."""
    return fetch_overpass_nodes("waste_basket", lat, lon, radius_m)


def fetch_recycling_centers(lat: float, lon: float,
                            radius_m: int = 1000) -> List[Dict]:
    """Fetches recycling center nodes from Overpass."""
    return fetch_overpass_nodes("recycling", lat, lon, radius_m)


def fetch_fuel_stations(lat: float, lon: float,
                        radius_m: int = 1000) -> List[Dict]:
    """Fetches fuel station nodes from Overpass."""
    return fetch_overpass_nodes("fuel", lat, lon, radius_m)


def osm_nodes_to_points(nodes: List[Dict],
                        id_offset: int = 1000) -> List[PointCollecte]:
    """
    Converts a list of OSM node dicts into PointCollecte instances.

    Args:
        nodes: List from fetch_overpass_nodes().
        id_offset: Starting ID to avoid collisions with existing graph IDs.

    Returns:
        List of PointCollecte with GPS coordinates set.
    """
    points = []
    for i, node in enumerate(nodes):
        name = node["tags"].get("name", f"OSM-{node['osm_id']}")
        pc = PointCollecte(
            id_point=id_offset + i,
            x=node["lon"],   # Use lon as x for abstract coords
            y=node["lat"],   # Use lat as y for abstract coords
            nom=name,
            lat=node["lat"],
            lon=node["lon"]
        )
        points.append(pc)
    return points
