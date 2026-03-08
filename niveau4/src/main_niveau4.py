"""
Script principal du Niveau 4 : Optimisation VRP (Vehicle Routing Problem).
Ce script réalise l'ordonnancement optimal des collectes pour minimiser la distance totale
parcourue par la flotte de camions. Inclut une phase de construction et une phase d'amélioration.
"""
import os
import sys

# Ajout du chemin racine pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau4.src.optimiseur_vrp import OptimiseurVRP
from niveau4.src.visualiseur_tournees import VisualiseurTournees
from niveau1.src.graphe_routier import GrapheRoutier
from niveau1.src.point_collecte import PointCollecte
from niveau2.src.camion import Camion
from commun.parseur_json import charger_json, sauvegarder_json

def main():
    """
    Fonction principale pour l'exécution du Niveau 4.
    1. Reconstruit le graphe à partir des données de Niveau 1.
    2. Initialise les camions.
    3. Exécute l'algorithme d'optimisation (Construction + Tabou/2-opt).
    4. Exporte les tournées et génère une représentation visuelle (carte).
    """
    # 1. Configuration des Chemins
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "input_niveau4.json")
    output_path = os.path.join(base_dir, "data", "output_niveau4.json")

    print(f"Chargement de {input_path}...")
    try:
        data = charger_json(input_path)
    except FileNotFoundError:
        print("Input Niveau 4 non trouvé, utilisation de valeurs par défaut.")
        data = {"configuration_vrp": {"nombre_camions": 3}}

    # Chargement du réseau routier (Niveau 1) pour avoir les coordonnées exactes
    input1_path = os.path.join(os.path.dirname(base_dir), "niveau1", "data", "input_niveau1.json")
    try:
        data1 = charger_json(input1_path)
    except FileNotFoundError:
        print("Erreur: Données du Niveau 1 indispensables pour la géographie.")
        return

    # Reconstruction du Graphe
    graphe = GrapheRoutier()
    points_dict = {}
    
    # Intégration du dépôt
    d_data = data1["depot"]
    depot = PointCollecte(d_data["id"], d_data["x"], d_data["y"], d_data["nom"])
    graphe.ajouter_sommet(depot)
    points_dict[depot.id] = depot
    
    # Intégration des points de collecte
    for p_data in data1["points_collecte"]:
        p = PointCollecte(p_data["id"], p_data["x"], p_data["y"], p_data.get("nom"))
        graphe.ajouter_sommet(p)
        points_dict[p.id] = p
        
    if "connexions" in data1:
        for c in data1["connexions"]:
            graphe.ajouter_arete(c["depart"], c["arrivee"], c["distance"])
            
    # Calcul de la matrice de base pour l'optimiseur
    graphe.matrice_distances()
    
    # 2. Configuration de la Flotte
    nb_camions = data.get("configuration_vrp", {}).get("nombre_camions", 2)
    camions = [Camion(i+1, 1000, 100) for i in range(nb_camions)]
    
    # 3. Optimisation
    print("Démarrage optimisation VRP...")
    optimiseur = OptimiseurVRP(graphe, camions, points_dict)
    
    # Phase 1 : Heuristique de construction (Plus proche voisin)
    tournees = optimiseur.construire_solution_initiale()
    dist_init = sum(t.calculer_distance(graphe) for t in tournees)
    print(f"Distance initiale: {dist_init:.2f}")
    
    # Phase 2 : Amélioration locale (Recherche Tabou / 2-opt)
    tournees_opt = optimiseur.recherche_tabou()
    dist_opt = sum(t.calculer_distance(graphe) for t in tournees_opt)
    print(f"Distance optimisée: {dist_opt:.2f}")
    
    # 4. Export des Résultats
    output = {
        "tournees_optimisees": [t.to_dict() for t in tournees_opt],
        "performance": {
            "distance_totale": dist_opt,
            "amelioration": dist_init - dist_opt
        }
    }
    
    sauvegarder_json(output, output_path)
    print(f"Résultats sauvegardés dans {output_path}")
    
    # Phase 5 : Visualisation Graphique
    print("Génération de la carte...")
    vis = VisualiseurTournees(tournees_opt, graphe)
    vis_path = os.path.join(base_dir, "visualisations", "carte_tournees.png")
    try:
        vis.generer_carte(vis_path)
        print(f"Carte sauvegardée dans {vis_path}")
    except Exception as e:
        print(f"Erreur lors de la génération de l'image : {e}")

if __name__ == "__main__":
    main()
