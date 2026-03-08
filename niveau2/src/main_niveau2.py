"""
Script principal du Niveau 2 : Affectation Camion-Zone.
Ce script charge les camions et les zones, réalise une affectation gloutonne
puis tente d'équilibrer les charges entre les camions avant de sauvegarder les résultats.
"""
import sys
import os

# Ajout du chemin racine du projet pour permettre les imports relatifs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from niveau2.src.affectateur_biparti import AffectateurBiparti
from commun.parseur_json import charger_json, sauvegarder_json

def main():
    """
    Fonction principale pour l'exécution du Niveau 2.
    1. Charge les données d'entrée (camions et zones).
    2. Réalise l'affectation gloutonne.
    3. Effectue un rééquilibrage heuristique des charges.
    4. Calcule les statistiques de performance.
    """
    # 1. Configuration des Chemins
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "input_niveau2.json")
    output_path = os.path.join(base_dir, "data", "output_niveau2.json")

    print(f"Chargement de {input_path}...")
    try:
        data = charger_json(input_path)
    except FileNotFoundError:
        print(f"Erreur: Fichier introuvable: {input_path}")
        return

    # Chargement des objets Camion et Zone
    camions = [Camion.from_dict(c) for c in data["camions"]]
    zones = [Zone.from_dict(z) for z in data["zones"]]

    # 2. Processus d'Affectation
    affectateur = AffectateurBiparti(camions, zones)
    
    print("Calcul de l'affectation gloutonne...")
    # Première phase : Affectation rapide
    resultats = affectateur.affectation_gloutonne()
    
    # Validation du respect des contraintes de base
    if affectateur.verifier_contraintes(resultats):
        print("Affectation valide.")
    else:
        print("Attention: Affectation initiale invalide.")

    # 3. Équilibrage des charges
    print("Tentative d'équilibrage des charges...")
    # Deuxième phase : Répartition plus homogène des volumes
    resultats_final = affectateur.equilibrage_charges(resultats)

    # 4. Analyse et Formatage de la Sortie
    affectation_output = []
    nb_camions_utilises = sum(1 for z_ids in resultats_final.values() if z_ids)
    zone_lookup = {z.id: z for z in zones}
    stats_charges = []
    
    for c_id, z_ids in resultats_final.items():
        charge = sum(zone_lookup[zid].volume_estime for zid in z_ids)
        stats_charges.append(charge)
        
        camion = next(c for c in camions if c.id == c_id)
        
        affectation_output.append({
            "camion_id": c_id,
            "zones_affectees": z_ids,
            "charge_totale": charge,
            "cout_estime": camion.cout_fixe,
            "pourcentage_utilisation": round((charge / camion.capacite) * 100, 1) if camion.capacite > 0 else 0
        })

    # Calcul des indicateurs statistiques (écart-type pour mesurer l'équilibre)
    import statistics
    charge_moyenne = statistics.mean(stats_charges) if stats_charges else 0
    ecart_type = statistics.stdev(stats_charges) if len(stats_charges) > 1 else 0

    output_data = {
        "affectation": affectation_output,
        "statistiques": {
            "nombre_camions_utilises": nb_camions_utilises,
            "charge_moyenne": round(charge_moyenne, 1),
            "ecart_type_charge": round(ecart_type, 1),
            "zones_non_affectees": [] 
        }
    }

    sauvegarder_json(output_data, output_path)
    print(f"Résultats sauvegardés dans {output_path}")

if __name__ == "__main__":
    main()
