"""
Composant de simulation temps réel pour le système de collecte de déchets.
Simule des capteurs IoT sur les bacs et des événements imprévus (pannes).
"""
import random
from commun.constantes import CO2_KG_PAR_LITRE, CONSOMMATION_L_PAR_KM

class CapteurIoT:
    """Simule un capteur IoT avec historique et prédiction."""
    def __init__(self, id_capteur: int, type_capteur: str = "niveau"):
        self.id = id_capteur
        self.type = type_capteur
        self.valeur = 0.0
        self.historique = []  # [(timestamp_minutes, valeur)]
        self.seuil_alerte = 80.0
        self.temps_courant = 0

    def mesurer(self) -> float:
        """Simule une mesure avec tendance + bruit (pas pur random)."""
        if self.type == "niveau":
            # Tendance: augmente de 1-4% par mesure + petit bruit
            augmentation = random.uniform(1.0, 4.0)
            bruit = random.gauss(0, 0.5)
            self.valeur = min(100.0, max(0.0, self.valeur + augmentation + bruit))
        elif self.type == "trafic":
            self.valeur = random.gauss(50, 20)  # Moyenne 50 km/h, écart-type 20
            self.valeur = max(5, min(120, self.valeur))
        
        self.temps_courant += 15  # Pas de 15 minutes
        self.historique.append((self.temps_courant, self.valeur))
        return self.valeur

    def detecter_urgence(self) -> bool:
        """Détecte si le capteur indique une urgence (> 90%)."""
        return self.valeur > 90.0

    def estimer_taux_remplissage(self, heures: int) -> float:
        """Prédit le niveau futur par régression linéaire sur l'historique."""
        if len(self.historique) < 2:
            return self.valeur
        
        # Régression linéaire simple: y = a*x + b
        n = len(self.historique)
        sum_x = sum(h[0] for h in self.historique)
        sum_y = sum(h[1] for h in self.historique)
        sum_xy = sum(h[0] * h[1] for h in self.historique)
        sum_x2 = sum(h[0] ** 2 for h in self.historique)
        
        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-9:
            return self.valeur
        
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        
        temps_futur = self.temps_courant + heures * 60
        prediction = a * temps_futur + b
        return min(100.0, max(0.0, prediction))

class SimulateurTempsReel:
    """
    Moteur de simulation gérant l'évolution de l'état du système au fil du temps.
    """
    def __init__(self, zones: list, camions: list):
        """
        Initialise le simulateur.
        
        Args:
            zones (list): Liste des zones de collecte.
            camions (list): Flotte de camions en service.
        """
        self.zones = zones
        self.camions = camions
        # Chaque zone est équipée d'un capteur de niveau
        self.capteurs_zones = {z.id: CapteurIoT(z.id, "niveau") for z in zones}
        self.evenements = []
        self.heure_simulation = 6  # Début à 6h du matin

    def executer_pas_de_temps(self, duree_minutes: int = 15):
        """
        Avance la simulation d'un certain nombre de minutes.
        Génère des événements aléatoires (alertes de remplissage, pannes).
        
        Args:
            duree_minutes (int): Le saut temporel à simuler.
            
        Returns:
            list: Liste des nouveaux événements survenus.
        """
        nouveaux_evenements = []
        
        # 1. Mise à jour de l'état des zones (remplissage progressif)
        for z in self.zones:
            # Taux de remplissage variable selon l'heure
            heure = self.heure_simulation % 24
            if 6 <= heure <= 9:      # Pic matinal
                taux_base = 4.0
            elif 11 <= heure <= 14:   # Pic midi
                taux_base = 3.5
            elif 17 <= heure <= 20:   # Pic soirée
                taux_base = 3.0
            elif 22 <= heure or heure < 6:  # Nuit
                taux_base = 0.5
            else:
                taux_base = 2.0
            taux = max(0, random.gauss(taux_base, 0.8))
            
            capteur = self.capteurs_zones[z.id]
            niveau_actuel = capteur.valeur
            nouveau_niveau = min(100, niveau_actuel + taux)
            capteur.valeur = nouveau_niveau
            
            # Alerte si le bac est presque plein
            if nouveau_niveau > 90 and niveau_actuel <= 90:
                # Standard Alert
                nouveaux_evenements.append({
                    "type": "ALERTE_REMPLISSAGE",
                    "zone_id": z.id,
                    "niveau": nouveau_niveau,
                    "message": f"Zone {z.id} remplie à {nouveau_niveau:.1f}%"
                })
                
                # Algorithmic Trust Constraint Log
                nouveaux_evenements.append({
                    "type": "RULE_ENFORCED",
                    "zone_id": z.id,
                    "niveau": nouveau_niveau,
                    "message": f"Constraint triggered: B(z{z.id}) > 90. Activating route dependency flag."
                })
            elif nouveau_niveau == 100 and niveau_actuel < 100:
                nouveaux_evenements.append({
                    "type": "RULE_ENFORCED",
                    "zone_id": z.id,
                    "niveau": nouveau_niveau,
                    "message": "Constraint triggered: Buffer Overflow. Routing penalized for C_Max(b)."
                })
        
        # 2. Simulation d'événements aléatoires (ex: Panne Camion)
        if random.random() < 0.01: # Probabilité de 1%
            camion_panne = random.choice(self.camions)
            nouveaux_evenements.append({
                "type": "PANNE_CAMION",
                "camion_id": camion_panne.id,
                "message": f"Camion {camion_panne.id} en panne!"
            })
            
        self.evenements.extend(nouveaux_evenements)
        # Garder seulement les 500 derniers événements en mémoire
        if len(self.evenements) > 500:
            self.evenements = self.evenements[-500:]
        
        self.heure_simulation += duree_minutes / 60.0
        return nouveaux_evenements

    def replanifier_urgence(self, points_urgents: list) -> list:
        """
        Réorganise les tournées pour traiter en priorité les points urgents.
        Retourne la liste des zones urgentes identifiées.
        """
        urgences = []
        for z in self.zones:
            capteur = self.capteurs_zones.get(z.id)
            if capteur and capteur.detecter_urgence():
                urgences.append({
                    "zone_id": z.id,
                    "niveau": capteur.valeur,
                    "priorite": "critique" if capteur.valeur > 95 else "haute"
                })
        
        for p_id in points_urgents:
            if p_id not in [u["zone_id"] for u in urgences]:
                urgences.append({
                    "zone_id": p_id,
                    "niveau": 100.0,
                    "priorite": "manuelle"
                })
        
        # Trier par niveau décroissant (plus rempli = plus urgent)
        urgences.sort(key=lambda u: u["niveau"], reverse=True)
        
        self.evenements.append({
            "type": "REPLANIFICATION_URGENCE",
            "points": [u["zone_id"] for u in urgences],
            "message": f"Replanification urgente pour {len(urgences)} points"
        })
        
        return urgences

    def calculer_emissions_co2(self, distance_totale_km: float) -> float:
        """Estime les émissions CO2 en kg pour une distance donnée."""
        litres = distance_totale_km * CONSOMMATION_L_PAR_KM
        return litres * CO2_KG_PAR_LITRE
