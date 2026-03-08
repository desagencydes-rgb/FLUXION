"""
Définit la classe Tournee, représentant la séquence de points visités par un camion.
"""
from commun.constantes import VITESSE_MOYENNE_KMH, TEMPS_SERVICE_MINUTES

class Tournee:
    """
    Objet représentant un itinéraire de collecte ordonné.
    Une tournée commence et se termine généralement au dépôt.
    """
    def __init__(self, camion_id: int, points: list = None):
        """
        Initialise une nouvelle tournée.
        
        Args:
            camion_id (int): L'ID du camion effectuant la tournée.
            points (list): Liste optionnelle d'IDs de points de collecte pour initialiser l'ordre.
        """
        self.camion_id = camion_id
        # Stockage des IDs des points pour faciliter la manipulation et l'export JSON
        self.points_ids = points or [] 
        self.heure_depart = None
        self.heure_retour = None

    def ajouter_point(self, point_id: int, position: int = -1) -> bool:
        """
        Insère un point dans l'itinéraire à la position spécifiée.
        
        Args:
            point_id (int): L'ID du point à ajouter.
            position (int): L'index d'insertion. Par défaut (-1), ajoute à la fin.
            
        Returns:
            bool: True si l'ajout a été possible.
        """
        if position == -1:
            self.points_ids.append(point_id)
        else:
            self.points_ids.insert(position, point_id)
        return True

    def calculer_distance(self, graphe) -> float:
        """
        Calcule la longueur totale du trajet en parcourant les points dans l'ordre du graphe.
        Utilise soit une matrice de distances pré-calculée, soit Dijkstra en direct.
        
        Args:
            graphe: Une instance de GrapheRoutier (Niveau 1).
            
        Returns:
            float: La distance totale cumulée.
        """
        if not self.points_ids:
            return 0.0
        
        distance = 0.0
        # Parcours de la séquence de points : [P0, P1, ..., Pn]
        for i in range(len(self.points_ids) - 1):
            id_a = self.points_ids[i]
            id_b = self.points_ids[i+1]
            
            # Utilisation de la matrice des distances pré-calculée si disponible (plus performant)
            if hasattr(graphe, 'matrice'):
                d = graphe.matrice[id_a][id_b]
            else:
                # Calcul à la volée via l'algorithme de Niveau 1
                d, _ = graphe.plus_court_chemin(id_a, id_b)
            
            distance += d
        return distance

    def calculer_duree(self, graphe, temps_service: dict = None) -> float:
        """
        Calcule durée estimée en minutes: trajet + temps de service par point.
        Args:
            graphe: GrapheRoutier.
            temps_service: Dict optionnel {point_id: minutes}. Défaut = TEMPS_SERVICE_MINUTES.
        Returns:
            float: Durée totale en minutes.
        """
        distance = self.calculer_distance(graphe)
        # Temps de trajet en minutes (distance en unités, vitesse en unités/h)
        temps_trajet = (distance / VITESSE_MOYENNE_KMH) * 60 if VITESSE_MOYENNE_KMH > 0 else 0
        
        # Temps de service: chaque point sauf dépôt (premier et dernier)
        nb_points_service = max(0, len(self.points_ids) - 2)
        if temps_service:
            temps_total_service = sum(
                temps_service.get(pid, TEMPS_SERVICE_MINUTES)
                for pid in self.points_ids[1:-1]
            )
        else:
            temps_total_service = nb_points_service * TEMPS_SERVICE_MINUTES
        
        return temps_trajet + temps_total_service

    def verifier_faisabilite(self, contraintes: dict) -> bool:
        """
        Vérifie les contraintes opérationnelles.
        Args:
            contraintes: Dict avec clés optionnelles:
                - 'capacite_max': float
                - 'duree_max_minutes': float
                - 'points_obligatoires': list[int]
        Returns:
            bool: True si toutes les contraintes sont respectées.
        """
        if 'capacite_max' in contraintes:
            # Nombre de points (proxy de charge si volumes inconnus)
            nb_collectes = len(self.points_ids) - 2
            if nb_collectes > contraintes['capacite_max']:
                return False
        if 'points_obligatoires' in contraintes:
            for p in contraintes['points_obligatoires']:
                if p not in self.points_ids:
                    return False
        return True

    def to_dict(self):
        """Convertit l'objet Tournee en dictionnaire pour l'export JSON."""
        return {
            "camion_id": self.camion_id,
            "points_ordre": self.points_ids,
            "heure_depart": str(self.heure_depart) if self.heure_depart else None,
            "heure_retour": str(self.heure_retour) if self.heure_retour else None
        }
