"""
Optimiseur VRP (Vehicle Routing Problem).
Utilise des méta-heuristiques pour minimiser la distance totale de collecte.
"""
from niveau4.src.tournee import Tournee
import random
import copy

class OptimiseurVRP:
    """
    Classe gérant l'optimisation des tournées de plusieurs véhicules.
    """
    def __init__(self, graphe, camions: list, points_collecte: dict):
        """
        Initialise l'optimiseur.
        
        Args:
            graphe (GrapheRoutier): Le réseau routier.
            camions (list): Liste des camions disponibles.
            points_collecte (dict): Dictionnaire des points à visiter.
        """
        self.graphe = graphe
        self.camions = camions
        self.points_collecte = points_collecte
        self.tournees = []
        self.volumes = {}
        
        # Pré-calculer la matrice des distances pour accélérer les itérations de l'optimiseur
        self.matrice_distances = self.graphe.matrice_distances(subset_ids=list(self.points_collecte.keys()))
        self.graphe.matrice = self.matrice_distances

    def construire_solution_initiale(self) -> list:
        """
        Génère une première solution valide via une heuristique gloutonne du "Plus Proche Voisin".
        Chaque camion dessert les points les plus proches jusqu'à ce qu'il n'y ait plus de points.
        
        Returns:
            list: Liste des objets Tournee créés.
        """
        points_a_visiter = set(self.points_collecte.keys())
        if 0 in points_a_visiter: points_a_visiter.remove(0) # Le dépôt (0) est géré à part
        
        tournees = []
        for c in self.camions:
            c.reset_charge()
        
        for camion in self.camions:
            if not points_a_visiter:
                break
                
            tournee = Tournee(camion.id)
            tournee.ajouter_point(0) # Départ du dépôt
            
            curr_point = 0
            
            while True:
                # Recherche du point le plus proche parmi les points restants
                meilleur_p = None
                meilleure_dist = float('inf')
                
                for p_id in points_a_visiter:
                    dist = self.matrice_distances[curr_point][p_id]
                    if dist < meilleure_dist:
                        # Vérifier la capacité du camion
                        volume_point = 1  # Poids unitaire par défaut
                        if hasattr(self, 'volumes') and p_id in self.volumes:
                            volume_point = self.volumes[p_id]
                        if camion.charge_actuelle + volume_point <= camion.capacite:
                            meilleure_dist = dist
                            meilleur_p = p_id
                
                if meilleur_p is not None:
                    volume = 1
                    if hasattr(self, 'volumes') and meilleur_p in self.volumes:
                        volume = self.volumes[meilleur_p]
                    camion.ajouter_charge(volume)
                    tournee.ajouter_point(meilleur_p)
                    points_a_visiter.remove(meilleur_p)
                    curr_point = meilleur_p
                else:
                    break
            
            tournee.ajouter_point(0) # Retour au dépôt
            tournees.append(tournee)
            
        self.tournees = tournees
        return tournees

    def algorithme_2opt(self, tournee: Tournee) -> Tournee:
        """
        Améliore une tournée en supprimant les croisements (heuristique 2-opt).
        Inverse itérativement des segments de la tournée si cela réduit la distance totale.
        
        Args:
            tournee (Tournee): La tournée à optimiser.
            
        Returns:
            Tournee: La tournée améliorée.
        """
        points = tournee.points_ids
        n = len(points)
        if n < 4: return tournee # Pas de permutation possible avec moins de 2 points intermédiaires
        
        best_points = points[:]
        best_dist = tournee.calculer_distance(self.graphe)
        
        improved = True
        while improved:
            improved = False
            # On parcourt toutes les paires possibles de segments à "décroiser"
            for i in range(1, n - 1):
                for j in range(i + 1, n - 1):
                    if j - i == 0: continue
                    
                    # Application du swap 2-opt : inversion de l'ordre des points entre i et j
                    new_points = best_points[:]
                    new_points[i:j+1] = best_points[i:j+1][::-1]
                    
                    t_temp = Tournee(tournee.camion_id, new_points)
                    d = t_temp.calculer_distance(self.graphe)
                    
                    # Si la nouvelle distance est meilleure, on valide le changement
                    if d < best_dist - 1e-9:
                        best_dist = d
                        best_points = new_points
                        improved = True
                        break 
                if improved: break
                        
        tournee.points_ids = best_points
        return tournee

    def recherche_tabou(self, iterations: int = 100) -> list:
        """
        Recherche Tabou : explore les voisinages en interdisant les mouvements récents
        pour éviter les cycles et s'échapper des optima locaux.
        """
        if not self.tournees:
            self.construire_solution_initiale()
        
        # Appliquer 2-opt initial sur chaque tournée
        for t in self.tournees:
            self.algorithme_2opt(t)
        
        import copy
        meilleure_solution = copy.deepcopy(self.tournees)
        meilleur_cout = sum(t.calculer_distance(self.graphe) for t in meilleure_solution)
        
        taille_tabou = max(7, len(self.tournees) * 2)
        liste_tabou = []  # Liste de mouvements interdits: (tournee_idx, i, j)
        
        stagnation = 0
        max_stagnation = max(20, iterations // 5)
        
        for it in range(iterations):
            meilleur_voisin = None
            meilleur_voisin_cout = float('inf')
            meilleur_mouvement = None
            
            for t_idx, tournee in enumerate(self.tournees):
                pts = tournee.points_ids
                n = len(pts)
                if n < 4:
                    continue
                
                for i in range(1, n - 1):
                    for j in range(i + 1, n - 1):
                        mouvement = (t_idx, i, j)
                        
                        # Tester le swap 2-opt
                        new_pts = pts[:]
                        new_pts[i:j+1] = pts[i:j+1][::-1]
                        
                        t_temp = Tournee(tournee.camion_id, new_pts)
                        cout_temp = t_temp.calculer_distance(self.graphe)
                        
                        # Calculer coût total avec ce changement
                        cout_total = cout_temp
                        for k, other_t in enumerate(self.tournees):
                            if k != t_idx:
                                cout_total += other_t.calculer_distance(self.graphe)
                        
                        est_tabou = mouvement in liste_tabou
                        
                        # Critère d'aspiration: accepter même si tabou si meilleur que le global
                        if est_tabou and cout_total >= meilleur_cout:
                            continue
                        
                        if cout_total < meilleur_voisin_cout:
                            meilleur_voisin_cout = cout_total
                            meilleur_voisin = (t_idx, new_pts)
                            meilleur_mouvement = mouvement
            
            if meilleur_voisin is None:
                break
            
            # Appliquer le meilleur mouvement
            t_idx, new_pts = meilleur_voisin
            self.tournees[t_idx].points_ids = new_pts
            
            # Ajouter à la liste tabou
            liste_tabou.append(meilleur_mouvement)
            if len(liste_tabou) > taille_tabou:
                liste_tabou.pop(0)
            
            # Mise à jour meilleure solution globale
            if meilleur_voisin_cout < meilleur_cout - 1e-9:
                meilleure_solution = copy.deepcopy(self.tournees)
                meilleur_cout = meilleur_voisin_cout
                stagnation = 0
            else:
                stagnation += 1
            
            if stagnation >= max_stagnation:
                break
        
        self.tournees = meilleure_solution
        return self.tournees
