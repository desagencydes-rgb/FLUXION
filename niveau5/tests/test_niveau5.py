import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau5.src.simulation import CapteurIoT, SimulateurTempsReel
from niveau5.src.optimiseur_mo import OptimiseurMultiObjectif
from niveau2.src.zone import Zone
from niveau2.src.camion import Camion
from niveau1.src.graphe_routier import GrapheRoutier
from niveau1.src.point_collecte import PointCollecte

class TestNiveau5(unittest.TestCase):
    def setUp(self):
        self.z1 = Zone(1, [], 80, 0, 0) # 80% rempli
        self.c1 = Camion(1, 100, 10 )
        self.sim = SimulateurTempsReel([self.z1], [self.c1])

    def test_5_1_capteur_iot(self):
        c = CapteurIoT(1, "niveau")
        val = c.mesurer()
        self.assertTrue(0 <= val <= 100)

    def test_5_2_simulation_alerte(self):
        # Force high fill rate to trigger alert.
        self.sim.capteurs_zones[1].valeur = 89.9
        events = self.sim.executer_pas_de_temps(15)
        
        found_alert = False
        for e in events:
            if e["type"] == "ALERTE_REMPLISSAGE" and e["zone_id"] == 1:
                found_alert = True
                break
        self.assertTrue(found_alert)

    def test_5_3_optimiseur_mo(self):
        # Setup minimal VRP context
        g = GrapheRoutier()
        p0 = PointCollecte(0, 0, 0)
        p1 = PointCollecte(1, 10, 0)
        g.ajouter_sommet(p0)
        g.ajouter_sommet(p1)
        g.ajouter_arete(0, 1, 10)
        g.matrice_distances()
        
        opt = OptimiseurMultiObjectif(g, [self.c1], {1: p1})
        tournees = opt.optimisation_bi_critere()
        
        # Verify result structure
        self.assertTrue(len(tournees) > 0)
        eval_res = opt.evaluer_solution(tournees)
        self.assertIn("distance_totale", eval_res)
        self.assertIn("ecart_charge", eval_res)

    def test_5_3_replanification_urgence(self):
        """Test que la replanification urgente s'exécute en < 2 secondes."""
        import time
        
        # Forcer un capteur en urgence
        self.sim.capteurs_zones[1].valeur = 95
        
        start = time.time()
        urgences = self.sim.replanifier_urgence([1])
        elapsed = time.time() - start
        
        self.assertTrue(elapsed < 2.0, f"Replanification a pris {elapsed:.2f}s (max: 2s)")
        self.assertTrue(len(urgences) > 0)
        self.assertEqual(urgences[0]["zone_id"], 1)

    def test_5_4_amelioration_multi_objectif(self):
        """Test que l'optimisation multi-objectif produit un front de Pareto."""
        g = GrapheRoutier()
        points = {}
        for i in range(6):
            p = PointCollecte(i, i * 2, i * 3)
            g.ajouter_sommet(p)
            points[i] = p
        
        ids = list(points.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                g.ajouter_arete(ids[i], ids[j])
        
        from niveau5.src.optimiseur_mo import OptimiseurMultiObjectif
        opt = OptimiseurMultiObjectif(g, [self.c1], points)
        pareto = opt.trouver_front_pareto(generations=10)
        
        self.assertTrue(len(pareto) >= 1, "Front de Pareto devrait avoir ≥ 1 solution")
        for sol in pareto:
            self.assertIn("distance_totale", sol["scores"])
            self.assertIn("emissions_co2", sol["scores"])

if __name__ == '__main__':
    unittest.main()
