"""
GPS Snapping — maps live driver GPS coordinates to the nearest vertex in the GrapheRoutier.
Used for Traccar driver heartbeats to position trucks on the road network graph.
"""
from typing import Tuple
from commun.geo_utils import haversine
from niveau1.src.graphe_routier import GrapheRoutier


def snap_to_graph(lat: float, lon: float, graphe: GrapheRoutier) -> Tuple[int, float]:
    """
    Finds the nearest vertex in the GrapheRoutier to the given GPS coordinate.

    Uses Haversine distance for accuracy when vertices have lat/lon.
    Falls back to Euclidean distance on abstract x/y coordinates.

    Args:
        lat: Driver's current latitude.
        lon: Driver's current longitude.
        graphe: The road network graph.

    Returns:
        Tuple of (vertex_id, distance_km). Returns (-1, inf) if graph is empty.
    """
    if not graphe.sommets:
        return -1, float('inf')

    best_id = -1
    best_dist = float('inf')

    for sid, sommet in graphe.sommets.items():
        if sommet.lat is not None and sommet.lon is not None:
            # GPS-based distance
            dist = haversine(lat, lon, sommet.lat, sommet.lon)
        else:
            # Fallback: treat lat as y, lon as x for abstract distances
            import math
            dist = math.sqrt((lon - sommet.x) ** 2 + (lat - sommet.y) ** 2)

        if dist < best_dist:
            best_dist = dist
            best_id = sid

    return best_id, best_dist


def snap_multiple(coordinates: list, graphe: GrapheRoutier) -> list:
    """
    Snaps multiple GPS coordinates to their nearest graph vertices.

    Args:
        coordinates: List of dicts with 'lat' and 'lon' keys.
        graphe: The road network graph.

    Returns:
        List of dicts with 'vertex_id', 'distance_km', 'lat', 'lon'.
    """
    results = []
    for coord in coordinates:
        vertex_id, dist = snap_to_graph(coord["lat"], coord["lon"], graphe)
        results.append({
            "vertex_id": vertex_id,
            "distance_km": round(dist, 4),
            "lat": coord["lat"],
            "lon": coord["lon"]
        })
    return results
