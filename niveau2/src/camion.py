"""
Définit la classe Camion utilisée pour la collecte des déchets.
"""

class Camion:
    """
    Représente un véhicule de collecte avec une capacité et des zones accessibles.
    """
    def __init__(self, id_camion: int, capacite: float, cout_fixe: float, zones_accessibles: list = None):
        """
        Initialise un nouveau camion.
        
        Args:
            id_camion (int): Identifiant unique du camion.
            capacite (float): Capacité maximale de chargement (kg).
            cout_fixe (float): Coût d'exploitation fixe journalier.
            zones_accessibles (list): Liste des IDs des zones que ce camion peut desservir.
        """
        self.id = id_camion
        self.capacite = capacite  # en kg
        self.cout_fixe = cout_fixe  # cout journalier
        self.zones_accessibles = zones_accessibles or [] # Liste d'IDs de zones
        self.charge_actuelle = 0.0

    def peut_acceder(self, zone_id: int) -> bool:
        """
        Vérifie si le camion a l'autorisation d'accéder à une zone donnée.
        
        Args:
            zone_id (int): L'identifiant de la zone à vérifier.
            
        Returns:
            bool: True si l'accès est autorisé.
        """
        return zone_id in self.zones_accessibles

    def ajouter_charge(self, charge: float) -> bool:
        """
        Tente d'ajouter un poids au chargement actuel du camion sans dépasser sa capacité.
        
        Args:
            charge (float): Le poids à ajouter (kg).
            
        Returns:
            bool: True si la charge a été acceptée, False sinon (capacité insuffisante).
        """
        if self.charge_actuelle + charge <= self.capacite:
            self.charge_actuelle += charge
            return True
        return False
    
    def reset_charge(self):
        """Réinitialise la charge actuelle du camion à zéro."""
        self.charge_actuelle = 0.0

    def to_dict(self):
        """Convertit l'objet Camion en dictionnaire pour l'export JSON."""
        return {
            "id": self.id,
            "capacite": self.capacite,
            "cout_fixe": self.cout_fixe,
            "zones_accessibles": self.zones_accessibles,
            "charge_actuelle": self.charge_actuelle
        }

    @staticmethod
    def from_dict(data):
        """Crée une instance de Camion à partir d'un dictionnaire de données."""
        return Camion(
            data["id"],
            data["capacite"],
            data["cout_fixe"],
            data.get("zones_accessibles", [])
        )

    def __repr__(self):
        return f"Camion(id={self.id}, cap={self.capacite}, charge={self.charge_actuelle})"
