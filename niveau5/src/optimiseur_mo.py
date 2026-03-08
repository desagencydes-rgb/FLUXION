"""
Optimiseur Multi-Objectif utilisant une version simplifiée de NSGA-II.
Objectifs: minimiser distance, minimiser CO2, maximiser équité.
"""
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from commun.constantes import CONSOMMATION_L_PAR_KM, CO2_KG_PAR_LITRE, SEUIL_AVERTISSEMENT
import copy
import random

class OptimiseurMultiObjectif(OptimiseurVRP):
    def __init__(self, graphe, camions, points_collecte):
        super().__init__(graphe, camions, points_collecte)
        self.solutions_pareto = []
        self.niveaux_remplissage = {}  # {point_id: fill_level_percent}

    def evaluer_solution(self, tournees: list) -> dict:
        """Évalue sur 4 axes: distance, CO2, satisfaction, écart de charge."""
        dist_totale = sum(t.calculer_distance(self.graphe) for t in tournees)
        co2 = dist_totale * CONSOMMATION_L_PAR_KM * CO2_KG_PAR_LITRE
        
        charges = []
        for t in tournees:
            nb_points = len(t.points_ids) - 2 if len(t.points_ids) >= 2 else 0
            charges.append(nb_points)
        ecart_charge = max(charges) - min(charges) if charges else 0
        
        # Satisfaction: % de zones à haut remplissage (>= seuil) couvertes par les tournées
        points_visites = set()
        for t in tournees:
            points_visites.update(t.points_ids)
        zones_prioritaires = [
            pid for pid, fill in self.niveaux_remplissage.items()
            if fill >= SEUIL_AVERTISSEMENT
        ]
        if zones_prioritaires:
            couvertes = sum(1 for pid in zones_prioritaires if pid in points_visites)
            satisfaction = (1.0 - couvertes / len(zones_prioritaires))  # Lower is better (invert)
        else:
            satisfaction = 0.0  # All satisfied if none are priority
        
        return {
            "distance_totale": dist_totale,
            "emissions_co2": co2,
            "satisfaction": satisfaction,
            "ecart_charge": ecart_charge
        }

    def domine(self, scores_a: dict, scores_b: dict) -> bool:
        """Retourne True si A domine B (meilleur ou égal sur tout, strictement meilleur sur au moins un)."""
        au_moins_un_meilleur = False
        for key in ["distance_totale", "emissions_co2", "satisfaction", "ecart_charge"]:
            if scores_a[key] > scores_b[key]:
                return False
            if scores_a[key] < scores_b[key]:
                au_moins_un_meilleur = True
        return au_moins_un_meilleur

    def trouver_front_pareto(self, population: list = None, generations: int = 50) -> list:
        """
        NSGA-II simplifié: génère des solutions variées par perturbation
        et filtre le front de Pareto (solutions non-dominées).
        """
        # Générer population initiale par perturbation
        if not self.tournees:
            self.construire_solution_initiale()
        
        solutions = []
        
        # Solution 1: optimisée distance (2-opt)
        sol_dist = copy.deepcopy(self.tournees)
        for t in sol_dist:
            self.algorithme_2opt(t)
        solutions.append(sol_dist)
        
        # Générer variations par permutation aléatoire
        for _ in range(min(generations, 20)):
            sol = copy.deepcopy(solutions[0])
            for t in sol:
                pts = t.points_ids
                if len(pts) > 4:
                    i = random.randint(1, len(pts) - 3)
                    j = random.randint(1, len(pts) - 3)
                    if i != j:
                        pts[i], pts[j] = pts[j], pts[i]
            solutions.append(sol)
        
        # Filtrer: garder seulement les non-dominées
        scored = [(sol, self.evaluer_solution(sol)) for sol in solutions]
        
        pareto = []
        for i, (sol_i, sc_i) in enumerate(scored):
            est_dominee = False
            for j, (sol_j, sc_j) in enumerate(scored):
                if i != j and self.domine(sc_j, sc_i):
                    est_dominee = True
                    break
            if not est_dominee:
                pareto.append({"solution": sol_i, "scores": sc_i})
        
        self.solutions_pareto = pareto
        return pareto

    def selectionner_solution(self, strategie: str = "equilibre") -> dict:
        """Sélectionne une solution du front de Pareto."""
        if not self.solutions_pareto:
            self.trouver_front_pareto()
        
        if not self.solutions_pareto:
            return {}
        
        if strategie == "distance":
            return min(self.solutions_pareto, key=lambda s: s["scores"]["distance_totale"])
        elif strategie == "co2":
            return min(self.solutions_pareto, key=lambda s: s["scores"]["emissions_co2"])
        elif strategie == "satisfaction":
            return min(self.solutions_pareto, key=lambda s: s["scores"]["satisfaction"])
        else:  # equilibre
            # Score normalisé pondéré sur 4 objectifs
            def score_equilibre(s):
                sc = s["scores"]
                return (sc["distance_totale"] * 0.3 + sc["emissions_co2"] * 0.25 +
                        sc["satisfaction"] * 0.25 + sc["ecart_charge"] * 0.2)
            return min(self.solutions_pareto, key=score_equilibre)

    def optimisation_bi_critere(self) -> list:
        """Retrocompatibilité: retourne la meilleure solution équilibrée."""
        pareto = self.trouver_front_pareto()
        if pareto:
            best = self.selectionner_solution("equilibre")
            self.tournees = best.get("solution", self.tournees)
        return self.tournees
