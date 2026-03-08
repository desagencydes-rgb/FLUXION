"""
Utilitaires géographiques: Haversine et OSRM pour distances routières réelles.
"""
import math
import urllib.request
import json

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en km entre deux points GPS (lat/lon en degrés).
    Formule de Haversine.
    """
    R = 6371.0  # Rayon de la Terre en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def osrm_distance_duree(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple:
    """
    Appelle le serveur OSRM public gratuit pour obtenir la distance routière réelle
    et la durée de trajet entre deux points GPS.
    
    Returns:
        tuple: (distance_km: float, duree_minutes: float)
        Retourne (haversine, estimation) en cas d'erreur réseau.
    """
    try:
        url = (f"https://router.project-osrm.org/route/v1/driving/"
               f"{lon1},{lat1};{lon2},{lat2}?overview=false")
        req = urllib.request.Request(url, headers={"User-Agent": "WasteCollectionProject/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            distance_km = route["distance"] / 1000.0
            duree_min = route["duration"] / 60.0
            return distance_km, duree_min
    except Exception:
        pass
    
    # Fallback: Haversine * 1.3 (facteur route), estimation de durée
    dist_vol = haversine(lat1, lon1, lat2, lon2)
    dist_route = dist_vol * 1.3
    duree = dist_route / 30.0 * 60.0  # 30 km/h moyen
    return dist_route, duree

def osrm_matrice_distances(points: list) -> list:
    """
    Calcule la matrice NxN des distances routières via OSRM Table API.
    
    Args:
        points: Liste de dicts avec clés 'lat' et 'lon'.
    
    Returns:
        list: Matrice NxN de distances en km. Fallback Haversine si erreur.
    """
    n = len(points)
    if n == 0:
        return []
    
    try:
        coords = ";".join(f"{p['lon']},{p['lat']}" for p in points)
        url = f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance"
        req = urllib.request.Request(url, headers={"User-Agent": "WasteCollectionProject/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        if data.get("code") == "Ok":
            # distances are in meters, convert to km
            matrice = []
            for row in data["distances"]:
                matrice.append([d / 1000.0 if d is not None else float('inf') for d in row])
            return matrice
    except Exception:
        pass
    
    # Fallback: Haversine matrix
    matrice = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrice[i][j] = haversine(
                    points[i]['lat'], points[i]['lon'],
                    points[j]['lat'], points[j]['lon']
                ) * 1.3
    return matrice
