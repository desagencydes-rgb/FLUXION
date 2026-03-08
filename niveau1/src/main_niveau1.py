"""
Script principal du Niveau 1 : Modèle de Base - Réseau Routier.
Ce script charge les données d'entrée, construit un graphe routier,
calcule la matrice des distances et les plus courts chemins depuis le dépôt,
puis sauvegarde les résultats dans un fichier JSON.
"""
import sys
import os

# Ajout du chemin racine du projet pour permettre les imports relatifs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau1.src.point_collecte import PointCollecte
from niveau1.src.graphe_routier import GrapheRoutier
from commun.parseur_json import charger_json, sauvegarder_json

def main():
    """
    Fonction principale pour l'exécution du Niveau 1.
    1. Initialise les chemins des fichiers.
    2. Charge les points de collecte (sommet) et les connexions (arêtes).
    3. Calcule la matrice complète des distances.
    4. Calcule les plus courts chemins (Dijkstra) pour l'output.
    """
    # 1. Configuration des Chemins
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "input_niveau1.json")
    output_path = os.path.join(base_dir, "data", "output_niveau1.json")

    print(f"Chargement de {input_path}...")
    try:
        data = charger_json(input_path)
    except FileNotFoundError:
        print(f"Erreur: Fichier introuvable: {input_path}")
        return

    # 2. Construction du Graphe
    graphe = GrapheRoutier()

    # Ajout du dépôt (point de départ des tournées)
    depot_data = data["depot"]
    depot = PointCollecte(depot_data["id"], depot_data["x"], depot_data["y"], depot_data["nom"])
    graphe.ajouter_sommet(depot)

    # Ajout des points de collecte
    for pt_data in data["points_collecte"]:
        pt = PointCollecte(pt_data["id"], pt_data["x"], pt_data["y"], pt_data.get("nom", ""))
        graphe.ajouter_sommet(pt)

    # Ajout des connexions (arêtes du graphe)
    if "connexions" in data:
        for conn in data["connexions"]:
            graphe.ajouter_arete(conn["depart"], conn["arrivee"], conn.get("distance"))
    else:
        # Si aucune connexion n'est fournie, le graphe est vide ou incomplet.
        pass

    # 3. Calculs algorithmiques
    print("Calcul de la matrice des distances...")
    # Calcule les distances entre TOUS les sommets du graphe
    matrice = graphe.matrice_distances()

    chemins_calcules = []
    # Calcul des chemins spécifiques demandés (Dépôt vers tous les autres points)
    ids = sorted(graphe.sommets.keys())
    depot_id = depot.id
    
    for dest_id in ids:
        if dest_id == depot_id:
            continue
        
        # Utilisation de l'algorithme de Dijkstra pour trouver le chemin le plus court
        dist, chemin = graphe.plus_court_chemin(depot_id, dest_id)
        if dist != float('inf'):
             chemins_calcules.append({
                "depart": depot_id,
                "arrivee": dest_id,
                "distance": round(dist, 1), # Arrondi pour la lisibilité
                "chemin": chemin
            })

    # 4. Sauvegarde des résultats
    output_data = {
        "matrice_distances": matrice,
        "chemins_calcules": chemins_calcules
    }
    
    sauvegarder_json(output_data, output_path)
    print(f"Résultats sauvegardés dans {output_path}")

if __name__ == "__main__":
    main()
