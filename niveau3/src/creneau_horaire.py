"""
Définit la classe CreneauHoraire représentant une période de temps pour la collecte.
"""
from datetime import datetime, timedelta

class CreneauHoraire:
    """
    Représente une tranche horaire spécifique un jour donné.
    Gère également la congestion simulée via un multiplicateur de coût.
    """
    def __init__(self, id_creneau: int, debut: str, fin: str, jour: str, cout_congestion: float = 1.0):
        """
        Initialise un créneau horaire.
        
        Args:
            id_creneau (int): Identifiant unique du créneau.
            debut (str): Heure de début au format "HH:MM".
            fin (str): Heure de fin au format "HH:MM".
            jour (str): Jour de la semaine.
            cout_congestion (float): Facteur de ralentissement (1.0 = fluide).
        """
        self.id = id_creneau
        self.debut_str = debut
        self.fin_str = fin
        self.debut = datetime.strptime(debut, "%H:%M")
        self.fin = datetime.strptime(fin, "%H:%M")
        self.jour = jour
        self.cout_congestion = cout_congestion # Multiplicateur de coût (temps de trajet)

    def duree(self) -> float:
        """
        Calcule la durée totale du créneau en heures.
        
        Returns:
            float: Durée en heures.
        """
        diff = self.fin - self.debut
        return diff.total_seconds() / 3600.0

    def chevauche(self, autre_creneau) -> bool:
        """
        Vérifie si ce créneau chevauche un autre créneau le même jour.
        
        Args:
            autre_creneau (CreneauHoraire): Le créneau à comparer.
            
        Returns:
            bool: True s'il y a un conflit temporel.
        """
        if self.jour != autre_creneau.jour:
            return False
        return (self.debut < autre_creneau.fin) and (self.fin > autre_creneau.debut)

    def to_dict(self):
        """Convertit le créneau en dictionnaire pour l'export JSON."""
        return {
            "id": self.id,
            "debut": self.debut_str,
            "fin": self.fin_str,
            "jour": self.jour,
            "niveau_congestion": self.cout_congestion
        }

    @staticmethod
    def from_dict(data):
        """Crée une instance de CreneauHoraire à partir d'un dictionnaire."""
        return CreneauHoraire(
            data["id"],
            data["debut"],
            data["fin"],
            data["jour"],
            data.get("niveau_congestion", 1.0)
        )

    def __repr__(self):
        return f"Creneau({self.id}, {self.jour}, {self.debut_str}-{self.fin_str})"
