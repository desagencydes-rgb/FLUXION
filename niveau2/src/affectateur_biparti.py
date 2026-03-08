"""
Implémente l'algorithme d'affectation des camions aux zones de collecte.
Utilise une approche gloutonne puis un rééquilibrage heuristique.
"""
import statistics
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from niveau1.src.graphe_routier import GrapheRoutier

class AffectateurBiparti:
    """
    Gère l'affectation entre un ensemble de camions et un ensemble de zones.
    """
    def __init__(self, camions: list, zones: list, graphe: GrapheRoutier = None):
        """
        Initialise l'affectateur.
        
        Args:
            camions (list): Liste d'objets Camion.
            zones (list): Liste d'objets Zone.
            graphe (GrapheRoutier): Optionnel.
        """
        self.camions = {c.id: c for c in camions} # Dict pour accès rapide
        self.zones = {z.id: z for z in zones}
        self.graphe = graphe # Optionnel pour niveau 2 simple

    def calculer_cout_affectation(self, camion_id: int, zone_id: int) -> float:
        """
        Calcule le coût d'affectation d'un camion à une zone.
        """
        camion = self.camions[camion_id]
        # Cout simple
        cout = camion.cout_fixe
        return cout

    def affectation_gloutonne(self) -> dict:
        """
        Affectation gloutonne basée sur coût minimal et capacité.
        Utilise la stratégie First Fit Decreasing.
        """
        affectation = {c_id: [] for c_id in self.camions}
        
        # Reset charges camions
        for c in self.camions.values():
            c.reset_charge()

        # Trier zones par volume décroissant
        zones_triees = sorted(self.zones.values(), key=lambda z: z.volume_estime, reverse=True)

        zones_non_affectees = []

        for zone in zones_triees:
            # Trouver meilleur camion disponible
            candidats = []
            for c_id, camion in self.camions.items():
                if camion.peut_acceder(zone.id) and (camion.charge_actuelle + zone.volume_estime <= camion.capacite):
                    cout = self.calculer_cout_affectation(c_id, zone.id)
                    candidats.append((cout, c_id))
            
            candidats.sort() # Moins cher d'abord
            
            if candidats:
                choisi_id = candidats[0][1]
                self.camions[choisi_id].ajouter_charge(zone.volume_estime)
                affectation[choisi_id].append(zone.id)
            else:
                zones_non_affectees.append(zone.id)
        
        return affectation

    def verifier_contraintes(self, affectation: dict) -> bool:
        """Vérifie le respect des capacités et de l'accessibilité."""
        for c_id, zone_ids in affectation.items():
            camion = self.camions.get(c_id)
            if not camion: continue
            
            # Verif capacité
            charge_totale = sum(self.zones[z_id].volume_estime for z_id in zone_ids)
            if charge_totale > camion.capacite:
                return False
            
            # Verif accessibilité
            for z_id in zone_ids:
                if not camion.peut_acceder(z_id):
                    return False
        return True

    def equilibrage_charges(self, affectation: dict) -> dict:
        """
        Tente de rééquilibrer les charges entre camions.
        """
        for _ in range(10): # Max iterations
            # Calcul charges actuelles
            charges = {}
            for c_id, z_ids in affectation.items():
                charges[c_id] = sum(self.zones[z].volume_estime for z in z_ids)
            
            if not charges: break
            
            max_c_id = max(charges, key=charges.get)
            min_c_id = min(charges, key=charges.get)
            
            diff = charges[max_c_id] - charges[min_c_id]
            moyenne = statistics.mean(charges.values()) if charges else 0
            seuil_ecart = 0.2 * moyenne # 20%
            
            if diff < seuil_ecart:
                break # Assez équilibré
            
            camion_min = self.camions[min_c_id]
            
            moved = False
            for z_id in affectation[max_c_id]:
                zone = self.zones[z_id]
                if camion_min.peut_acceder(z_id) and \
                   (charges[min_c_id] + zone.volume_estime <= camion_min.capacite):
                   
                    new_max = charges[max_c_id] - zone.volume_estime
                    new_min = charges[min_c_id] + zone.volume_estime
                    new_diff = abs(new_max - new_min)
                    
                    if new_diff < diff:
                        affectation[max_c_id].remove(z_id)
                        affectation[min_c_id].append(z_id)
                        moved = True
                        break
            
            if not moved:
                break
                
        return affectation
