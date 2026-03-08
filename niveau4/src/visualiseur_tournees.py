"""
Composant de visualisation cartographique des tournées optimisées.
"""
import matplotlib.pyplot as plt

class VisualiseurTournees:
    """
    Génère des images représentant les itinéraires sur un plan 2D.
    """
    def __init__(self, tournees: list, graphe):
        """
        Initialise le visualiseur.
        
        Args:
            tournees (list): Liste des objets Tournee à afficher.
            graphe (GrapheRoutier): Le réseau pour récupérer les coordonnées.
        """
        self.tournees = tournees
        self.graphe = graphe

    def generer_carte(self, fichier_sortie: str) -> None:
        """
        Génère une image PNG montrant les points de collecte, le dépôt et les tracés
        des différents camions (identifiés par des couleurs distinctes).
        
        Args:
            fichier_sortie (str): Chemin d'enregistrement de l'image.
        """
        plt.figure(figsize=(10, 8))
        
        # Affichage de tous les sommets du réseau en gris
        x = [p.x for p in self.graphe.sommets.values()]
        y = [p.y for p in self.graphe.sommets.values()]
        plt.scatter(x, y, c='gray', label='Points de collecte')
        
        # Identification visuelle du Dépôt (Point 0)
        depot = self.graphe.sommets[0]
        plt.scatter(depot.x, depot.y, c='red', s=100, marker='s', label='Dépôt central')
        
        # Tracé de chaque tournée avec une couleur différente
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        for idx, t in enumerate(self.tournees):
            path_x = []
            path_y = []
            for pid in t.points_ids:
                p = self.graphe.sommets[pid]
                path_x.append(p.x)
                path_y.append(p.y)
            
            plt.plot(path_x, path_y, c=colors[idx % len(colors)], label=f'Camion {t.camion_id}')
            
        plt.legend()
        plt.title('Visualisation des Tournées Optimisées (VRP)')
        plt.xlabel('Coordonnée X')
        plt.ylabel('Coordonnée Y')
        plt.savefig(fichier_sortie)
        plt.close()
