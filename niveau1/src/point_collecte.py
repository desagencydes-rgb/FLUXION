"""
Définit la classe PointCollecte, représentant un sommet dans le réseau de collecte.
"""
from commun.outils_math import distance_euclidienne

class PointCollecte:
    """
    Représente un point géographique sur le réseau (dépôt ou point de collecte).
    """
    def __init__(self, id_point: int, x: float, y: float, nom: str = "", lat: float = None, lon: float = None):
        """
        Initialise un nouveau point de collecte.
        
        Args:
            id_point (int): Identifiant unique du point.
            x (float): Coordonnée X (abstraite, ex: grille).
            y (float): Coordonnée Y (abstraite, ex: grille).
            nom (str): Nom facultatif pour le point.
            lat (float, optional): Latitude GPS. Defaults to None.
            lon (float, optional): Longitude GPS. Defaults to None.
        """
        self.id = id_point
        self.x = x  # Coordonnée abstraite (ex: grille)
        self.y = y  # Coordonnée abstraite (ex: grille)
        self.nom = nom
        self.lat = lat  # Latitude GPS (optionnelle)
        self.lon = lon  # Longitude GPS (optionnelle)

    def distance_vers(self, autre_point) -> float:
        """
        Calcule la distance euclidienne directe vers un autre point.
        
        Args:
            autre_point (PointCollecte): Le point de destination.
            
        Returns:
            float: La distance à vol d'oiseau.
        """
        return distance_euclidienne(self, autre_point)

    def to_dict(self):
        """Convertit le point en dictionnaire pour la sérialisation."""
        d = {"id": self.id, "x": self.x, "y": self.y, "nom": self.nom}
        if self.lat is not None:
            d["lat"] = self.lat
            d["lon"] = self.lon
        return d
    
    @staticmethod
    def from_dict(data):
        """Crée une instance PointCollecte à partir d'un dictionnaire."""
        return PointCollecte(
            data["id"], data["x"], data["y"], data.get("nom", ""),
            lat=data.get("lat"), lon=data.get("lon")
        )

    def __repr__(self):
        return f"PointCollecte(id={self.id}, x={self.x}, y={self.y}, nom='{self.nom}')"
