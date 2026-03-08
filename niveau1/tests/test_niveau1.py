import unittest
import sys
import os

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau1.src.point_collecte import PointCollecte
from niveau1.src.graphe_routier import GrapheRoutier

class TestNiveau1(unittest.TestCase):
    def setUp(self):
        self.graphe = GrapheRoutier()
        self.p0 = PointCollecte(0, 0, 0, "Depot")
        self.p1 = PointCollecte(1, 3, 4, "P1") # 3,4,5 triangle
        self.p2 = PointCollecte(2, 6, 0, "P2")
        
        self.graphe.ajouter_sommet(self.p0)
        self.graphe.ajouter_sommet(self.p1)
        self.graphe.ajouter_sommet(self.p2)

    def test_1_1_matrice_distances(self):
        # 0 -> 1 : dist 5
        # 1 -> 2 : dist sqrt(3^2 + 4^2) = 5 if coords were specific, but here:
        # p1(3,4) -> p2(6,0) : dx=3, dy=-4 -> dist 5
        # 0 -> 2 : dist 6
        
        self.graphe.ajouter_arete(0, 1) # Auto calc
        self.graphe.ajouter_arete(1, 2)
        self.graphe.ajouter_arete(0, 2)
        
        matrice = self.graphe.matrice_distances()
        # Sommets sorted ids: 0, 1, 2
        
        # 0->1 = 5.0
        self.assertEqual(matrice[0][1], 5.0)
        # 1->2 = 5.0
        self.assertEqual(matrice[1][2], 5.0)
        # 0->2 direct = 6.0. Via 1 = 5+5=10. Shortest is 6.
        self.assertEqual(matrice[0][2], 6.0)

    def test_1_2_chemin_existant(self):
        self.graphe.ajouter_arete(0, 1)
        self.graphe.ajouter_arete(1, 2)
        # Pas d'arete directe 0-2
        
        dist, chemin = self.graphe.plus_court_chemin(0, 2)
        self.assertEqual(dist, 10.0)
        self.assertEqual(chemin, [0, 1, 2])

    def test_1_3_symetrie(self):
        self.graphe.ajouter_arete(0, 1)
        dist01 = self.graphe.sommets[0].distance_vers(self.graphe.sommets[1])
        dist10 = self.graphe.sommets[1].distance_vers(self.graphe.sommets[0])
        self.assertEqual(dist01, dist10)

    def test_1_4_inegalite_triangulaire(self):
        # A(0,0), B(0,1), C(1,0)
        pa = PointCollecte(10, 0, 0)
        pb = PointCollecte(11, 0, 1)
        pc = PointCollecte(12, 1, 0)
        
        dab = pa.distance_vers(pb)
        dbc = pb.distance_vers(pc)
        dac = pa.distance_vers(pc)
        
        # dac <= dab + dbc
        self.assertTrue(dac <= dab + dbc)

if __name__ == '__main__':
    unittest.main()
