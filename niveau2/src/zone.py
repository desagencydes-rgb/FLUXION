"""
Définit la classe Zone, regroupant plusieurs points de collecte.
"""

class Zone:
    """
    Représente une zone géographique de collecte regroupant plusieurs points.
    """
    def __init__(self, id_zone: int, points: list, volume_estime: float, centre_x: float, centre_y: float):
        """
        Initialise une nouvelle zone.
        
        Args:
            id_zone (int): Identifiant unique de la zone.
            points (list): Liste des IDs des points de collecte inclus dans cette zone.
            volume_estime (float): Volume total estimé des déchets dans la zone.
            centre_x (float): Coordonnée X du centre de gravité de la zone.
            centre_y (float): Coordonnée Y du centre de gravité de la zone.
        """
        self.id = id_zone
        self.points = points  # Liste d'IDs de points de collecte
        self.volume_estime = volume_estime # Volume ou poids total estimé
        self.centre = (centre_x, centre_y)

    def to_dict(self):
        """Convertit l'objet Zone en dictionnaire pour l'export JSON."""
        return {
            "id": self.id,
            "points": self.points,
            "volume_moyen": self.volume_estime, # Mapping vers le nom de champ attendu par l'input
            "centre": {"x": self.centre[0], "y": self.centre[1]}
        }

    @staticmethod
    def from_dict(data):
        """Crée une instance de Zone à partir d'un dictionnaire de données."""
        centre = data.get("centre", {"x": 0, "y": 0})
        return Zone(
            data["id"],
            data.get("points", []),
            data.get("volume_moyen", 0.0),
            centre["x"],
            centre["y"]
        )

    def __repr__(self):
        return f"Zone(id={self.id}, vol={self.volume_estime})"
