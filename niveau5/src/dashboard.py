"""
Outil de monitoring et de visualisation des indicateurs système.
Affiche les événements temps réel et les KPIs de performance.
"""
import json

class DashboardTempsReel:
    """
    Console de supervision pour l'opérateur de collecte.
    """
    def __init__(self):
        self.logs = []
        
    def afficher_etat(self, evenements: list, indicateurs: dict):
        """
        Met à jour l'affichage avec les dernières données de simulation.
        
        Args:
            evenements (list): Liste des nouveaux événements (alertes, pannes).
            indicateurs (dict): Valeurs courantes des KPIs (distance, charges, etc.).
        """
        print("\n--- DASHBOARD DE SUPERVISION TEMPS RÉEL ---\n")
        
        if evenements:
            print(f"!!! {len(evenements)} NOUVEAUX ÉVÉNEMENTS DÉTECTÉS !!!")
            for evt in evenements:
                print(f"  [{evt['type']}] {evt['message']}")
                self.logs.append(evt)
        else:
            print("  Système stable : Aucun incident signalé.")
            
        print("\nIndicateurs de Performance (KPIs) :")
        for k, v in indicateurs.items():
            print(f"  {k}: {v}")
            
        print("\n" + "="*40 + "\n")

    def exporter_rapport(self, chemin_fichier: str):
        """
        Sauvegarde l'historique des événements dans un fichier JSON.
        """
        with open(chemin_fichier, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=4, ensure_ascii=False)
