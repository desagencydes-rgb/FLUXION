from niveau5.src.simulation import SimulateurTempsReel
from niveau5.src.optimiseur_mo import OptimiseurMultiObjectif
from niveau5.src.dashboard import DashboardTempsReel
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from niveau1.src.point_collecte import PointCollecte
from niveau1.src.graphe_routier import GrapheRoutier
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from commun.parseur_json import charger_json, sauvegarder_json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "input_niveau5.json")
    output_path = os.path.join(base_dir, "data", "output_niveau5.json")
    
    # CHARGEMENT DONNEES
    # On va réutiliser les données niveau 2 pour zones/camions
    input2_path = os.path.join(os.path.dirname(base_dir), "niveau2", "data", "input_niveau2.json")
    try:
        data2 = charger_json(input2_path)
        zones = [Zone.from_dict(z) for z in data2["zones"]]
        camions = [Camion.from_dict(c) for c in data2["camions"]]
    except FileNotFoundError:
        print("Données niveau 2 manquantes.")
        # Fallback mocks
        zones = [Zone(i, [], 50, 0, 0) for i in range(1, 6)]
        camions = [Camion(1, 100, 10)]

    # Graph setup (reuse Level 1 or empty mock for simulation focus)
    graphe = GrapheRoutier()
    # Mock graph points for optimization to work (even if minimal)
    graphe.ajouter_sommet(PointCollecte(0, 0, 0)) # Depot
    for i, z in enumerate(zones, 1):
        graphe.ajouter_sommet(PointCollecte(z.id, i*10, i*10)) # Mock coords
        graphe.ajouter_arete(0, z.id, 10) # Mock dist
    graphe.matrice_distances()

    # SIMULATION
    sim = SimulateurTempsReel(zones, camions)
    dashboard = DashboardTempsReel()
    
    print("Démarrage de la simulation temps réel (4 pas de temps)...")
    
    rapport_events = []
    
    for pas in range(4): # Simuler 1 heure en 4 pas de 15 min
        print(f"\n--- Pas {pas+1} ---")
        events = sim.executer_pas_de_temps(15)
        
        # Dashboard update
        indicateurs = {
            "nb_alertes": len(events),
            "zones_critiques": [e["zone_id"] for e in events if e["type"] == "ALERTE_REMPLISSAGE"]
        }
        dashboard.afficher_etat(events, indicateurs)
        rapport_events.extend(events)
        
        # Réaction optimisation si alerte majeure ?
        if events:
            print("  -> Déclenchement ré-optimisation...")
            # Ici on appellerait l'optimiseur dynamique
            # opt = OptimiseurMultiObjectif(...)
            # new_plan = opt.optimisation_bi_critere(...)
            pass

    # Sauvegarde
    simulation_log = os.path.join(base_dir, "logs", "simulation.json")
    if not os.path.exists(os.path.dirname(simulation_log)):
        os.makedirs(os.path.dirname(simulation_log))
        
    dashboard.exporter_rapport(simulation_log)
    print(f"\nRapport simulation sauvegardé: {simulation_log}")

if __name__ == "__main__":
    main()
