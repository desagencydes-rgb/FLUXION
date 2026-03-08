"""
Gère les contraintes temporelles complexes : fenêtres de zones, pauses camions, et restrictions de nuit.
"""
from datetime import datetime

class ContrainteTemporelle:
    """
    Système de validation des horaires pour s'assurer que les collectes respectent
    les règlements et les contraintes opérationnelles.
    """
    def __init__(self):
        self.fenetres_zone = {}  # { zone_id: (debut_dt, fin_dt) }
        self.pauses_camion = {}  # { camion_id: [{"debut": dt, "duree": h}] }
        self.zones_interdites_nuit = set() # Ensemble d'IDs de zones

    def ajouter_fenetre_zone(self, zone_id: int, debut: str, fin: str):
        """
        Définit une plage horaire autorisée pour la collecte dans une zone.
        """
        self.fenetres_zone[zone_id] = (
            datetime.strptime(debut, "%H:%M"),
            datetime.strptime(fin, "%H:%M")
        )

    def ajouter_pause_camion(self, camion_id: int, debut: str, duree_h: float):
        """
        Définit une pause obligatoire pour un conducteur de camion.
        """
        d = datetime.strptime(debut, "%H:%M")
        if camion_id not in self.pauses_camion:
            self.pauses_camion[camion_id] = []
        self.pauses_camion[camion_id].append({"debut": d, "duree": duree_h})

    def est_realisable(self, camion_id: int, zone_id: int, creneau) -> bool:
        """
        Vérifie si une affectation est temporellement possible à un créneau donné.
        
        Vérifications effectuées :
        1. Fenêtre d'ouverture de la zone.
        2. Conflit avec les pauses du camion (A implémenter plus finement).
        3. Restrictions de collecte nocturnes.
        
        Args:
            camion_id (int): ID du camion.
            zone_id (int): ID de la zone.
            creneau (CreneauHoraire): Le créneau proposé.
            
        Returns:
            bool: True si toutes les contraintes sont satisfaites.
        """
        # 1. Limitation par Fenêtre Zone
        if zone_id in self.fenetres_zone:
            f_debut, f_fin = self.fenetres_zone[zone_id]
            # La collecte doit commencer et finir à l'intérieur de la fenêtre
            if creneau.debut < f_debut or creneau.fin > f_fin:
                return False
        
        # 2. Vérification des Pauses Camion (intersection complète)
        if camion_id in self.pauses_camion:
            for pause in self.pauses_camion[camion_id]:
                from datetime import timedelta
                pause_debut = pause["debut"]
                pause_fin = pause_debut + timedelta(hours=pause["duree"])
                # Rejet si le créneau chevauche la fenêtre de pause
                if creneau.debut < pause_fin and creneau.fin > pause_debut:
                    return False

        # 3. Restriction de Nuit (ex: Interdiction entre 22h et 06h pour certaines zones bruyantes)
        if zone_id in self.zones_interdites_nuit:
            usage_nuit = (creneau.debut.hour >= 22 or creneau.debut.hour < 6)
            if usage_nuit:
                return False

        return True

    def calculer_penalite(self, camion_id: int, zone_id: int, creneau) -> float:
        """
        Calcule une pénalité de coût basée sur la congestion du créneau.
        
        Returns:
            float: Coût additionnel.
        """
        return (creneau.cout_congestion - 1.0) * 10
