"""
Script principal du Niveau 3 : Planification Temporelle.
Ce script intègre les affectations spatiales (Niveau 2) dans un calendrier hebdomadaire
en tenant compte des créneaux horaires, de la congestion et des contraintes de temps.
"""
from niveau3.src.creneau_horaire import CreneauHoraire
from niveau3.src.contrainte_temporelle import ContrainteTemporelle
from niveau3.src.planificateur_triparti import PlanificateurTriparti
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from niveau2.src.affectateur_biparti import AffectateurBiparti
from commun.parseur_json import charger_json, sauvegarder_json
import os
import sys

# Ajout du chemin racine du projet pour faciliter les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

def main():
    """
    Fonction principale pour l'exécution du Niveau 3.
    1. Charge les données de base (camions/zones) du Niveau 2.
    2. Charge les contraintes temporelles et créneaux du Niveau 3.
    3. Génère un planning hebdomadaire optimisé.
    4. Exporte les résultats et les indicateurs de performance.
    """
    # 1. Configuration des Chemins
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "input_niveau3.json")
    output_path = os.path.join(base_dir, "data", "output_niveau3.json")

    print(f"Chargement de {input_path}...")
    try:
        data = charger_json(input_path)
    except FileNotFoundError:
        print(f"Erreur: Fichier introuvable: {input_path}")
        return

    # Chargement des ressources de base (Niveau 2) nécessaires à la planification
    input2_path = os.path.join(os.path.dirname(base_dir), "niveau2", "data", "input_niveau2.json")
    try:
        data2 = charger_json(input2_path)
        camions = [Camion.from_dict(c) for c in data2["camions"]]
        zones = [Zone.from_dict(z) for z in data2["zones"]]
    except FileNotFoundError:
        print("Erreur: Données de base du Niveau 2 non trouvées.")
        return

    # 2. Chargement des données spécifiques au Niveau 3
    creneaux = [CreneauHoraire.from_dict(c) for c in data["creneaux"]]
    
    # Configuration du gestionnaire de contraintes
    contraintes = ContrainteTemporelle()
    ct_data = data["contraintes_temporelles"]
    
    # Ajout des fenêtres de temps spécifiques aux zones
    for fz in ct_data.get("fenetres_zone", []):
        contraintes.ajouter_fenetre_zone(fz["zone_id"], fz["debut"], fz["fin"])
    
    # Ajout des temps de pause conducteurs
    for pc in ct_data.get("pauses_obligatoires", []):
        contraintes.ajouter_pause_camion(pc["camion_id"], pc["debut"], pc["duree"])
        
    # Zones sensibles interdisant le passage de nuit
    for zi in ct_data.get("zones_interdites_nuit", []):
        contraintes.zones_interdites_nuit.add(zi)

    # 3. Initialisation et exécution du Planificateur
    affectateur = AffectateurBiparti(camions, zones)
    planificateur = PlanificateurTriparti(affectateur, contraintes, creneaux)
    
    print("Génération du plan hebdomadaire...")
    # Calcul du planning
    plan = planificateur.generer_plan_optimal()
    
    # Calcul des indicateurs de performance (KPIs)
    stats = planificateur.evaluer_plan(plan)
    
    # 4. Exportation des résultats
    output_data = {
        "planification_hebdomadaire": plan,
        "indicateurs": stats
    }
    
    sauvegarder_json(output_data, output_path)
    print(f"Résultats sauvegardés dans {output_path}")

if __name__ == "__main__":
    main()
