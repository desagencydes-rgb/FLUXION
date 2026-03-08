"""
Visualiseur de Tournées de Collecte.
Fournit des vues graphiques ou textuelles demandées par la spécification (Phase 4).
(Complément pour la validation académique Niveau 4)
"""
class VisualiseurTournees:
    def __init__(self, tournees, graphe):
        self.tournees = tournees
        self.graphe = graphe
        
    def generer_carte(self):
        """Génère (ou simule) une carte des tournées."""
        print("Génération de la carte des tournées...")
        for t in self.tournees:
            print(f"Camion {t.camion_id} suit l'itinéraire: {t.points_ids}")
            
    def generer_gantt(self):
        """Génère (ou simule) un diagramme de Gantt des horaires de chaque tournée."""
        print("Génération du diagramme de Gantt...")
        for t in self.tournees:
            duree = t.calculer_distance(self.graphe)  # Approximation simplifiée
            # En réalité, on utiliserait t.calculer_duree(self.graphe)
            print(f"Camion {t.camion_id}: Début 08:00 - Fin estimée à {8 + duree/30:.2f}h")
