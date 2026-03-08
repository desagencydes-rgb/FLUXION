"""
Tests for the Live Bridge module.
Covers GPS snapping, RBAC enforcement, and data client parsing.
"""
import unittest
import sys
import os

# Ensure project root is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from niveau1.src.graphe_routier import GrapheRoutier
from niveau1.src.point_collecte import PointCollecte


class TestGPSSnapper(unittest.TestCase):
    """Tests for gps_snapper module."""

    def setUp(self):
        self.graphe = GrapheRoutier()
        # Create a graph with GPS-enabled points
        self.p0 = PointCollecte(0, 2.3522, 48.8566, "Depot",
                                lat=48.8566, lon=2.3522)   # Paris center
        self.p1 = PointCollecte(1, 2.2945, 48.8584, "Eiffel",
                                lat=48.8584, lon=2.2945)   # Eiffel Tower
        self.p2 = PointCollecte(2, 2.3499, 48.8530, "Notre-Dame",
                                lat=48.8530, lon=2.3499)   # Notre-Dame

        self.graphe.ajouter_sommet(self.p0)
        self.graphe.ajouter_sommet(self.p1)
        self.graphe.ajouter_sommet(self.p2)

    def test_snap_exact_match(self):
        """Snapping a coordinate exactly at a vertex should return that vertex."""
        from live_bridge.gps_snapper import snap_to_graph
        vid, dist = snap_to_graph(48.8566, 2.3522, self.graphe)
        self.assertEqual(vid, 0)
        self.assertAlmostEqual(dist, 0.0, places=3)

    def test_snap_closest_vertex(self):
        """Snapping near Notre-Dame should return vertex 2."""
        from live_bridge.gps_snapper import snap_to_graph
        # Slightly offset from Notre-Dame
        vid, dist = snap_to_graph(48.8532, 2.3501, self.graphe)
        self.assertEqual(vid, 2)
        self.assertTrue(dist < 0.05)  # Should be very close (< 50m)

    def test_snap_empty_graph(self):
        """Snapping on empty graph returns -1."""
        from live_bridge.gps_snapper import snap_to_graph
        empty_g = GrapheRoutier()
        vid, dist = snap_to_graph(48.8566, 2.3522, empty_g)
        self.assertEqual(vid, -1)

    def test_snap_multiple(self):
        """Snapping multiple coordinates returns correct length."""
        from live_bridge.gps_snapper import snap_multiple
        coords = [
            {"lat": 48.8566, "lon": 2.3522},
            {"lat": 48.8584, "lon": 2.2945}
        ]
        results = snap_multiple(coords, self.graphe)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["vertex_id"], 0)
        self.assertEqual(results[1]["vertex_id"], 1)


class TestRBAC(unittest.TestCase):
    """Tests for RBAC role checking (unit-level, no HTTP)."""

    def test_role_hierarchy(self):
        from live_bridge.rbac import check_permission
        # driver can access driver endpoints
        self.assertTrue(check_permission("driver", "driver"))
        # driver CANNOT access fleet_manager endpoints
        self.assertFalse(check_permission("driver", "fleet_manager"))
        # fleet_manager CAN access driver endpoints
        self.assertTrue(check_permission("fleet_manager", "driver"))
        # super_admin can access everything
        self.assertTrue(check_permission("super_admin", "fleet_manager"))
        self.assertTrue(check_permission("super_admin", "driver"))

    def test_weights_blocked_for_driver(self):
        from live_bridge.rbac import get_required_role, check_permission
        required = get_required_role("/api/simulation/weights")
        self.assertEqual(required, "fleet_manager")
        self.assertFalse(check_permission("driver", required))

    def test_gps_snap_allowed_for_driver(self):
        from live_bridge.rbac import get_required_role, check_permission
        required = get_required_role("/live/gps-snap")
        self.assertEqual(required, "driver")
        self.assertTrue(check_permission("driver", required))

    def test_health_open(self):
        from live_bridge.rbac import get_required_role
        required = get_required_role("/live/health")
        self.assertEqual(required, "driver")


class TestOverpassParsing(unittest.TestCase):
    """Tests for Overpass client node parsing."""

    def test_osm_nodes_to_points(self):
        from live_bridge.overpass_client import osm_nodes_to_points
        fake_nodes = [
            {"osm_id": 123, "lat": 48.8566, "lon": 2.3522, "tags": {"name": "Bin 1"}},
            {"osm_id": 456, "lat": 48.8570, "lon": 2.3530, "tags": {}},
        ]
        points = osm_nodes_to_points(fake_nodes, id_offset=5000)

        self.assertEqual(len(points), 2)
        self.assertEqual(points[0].id, 5000)
        self.assertEqual(points[0].nom, "Bin 1")
        self.assertAlmostEqual(points[0].lat, 48.8566)
        self.assertAlmostEqual(points[0].lon, 2.3522)

        # Second has auto-generated name
        self.assertEqual(points[1].id, 5001)
        self.assertIn("OSM-456", points[1].nom)


class TestGeoapifyParsing(unittest.TestCase):
    """Tests for Geoapify client POI parsing."""

    def test_pois_to_points(self):
        from live_bridge.geoapify_client import pois_to_points
        fake_pois = [
            {
                "place_id": "abc",
                "name": "Le Bistrot",
                "lat": 48.8566,
                "lon": 2.3522,
                "category": "restaurant",
                "priority": 1.5,
                "address": "1 Rue Test"
            }
        ]
        points = pois_to_points(fake_pois, id_offset=9000)

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].id, 9000)
        self.assertIn("restaurant", points[0].nom)
        self.assertIn("Le Bistrot", points[0].nom)


class TestIntegration(unittest.TestCase):
    """Integration: live data → PointCollecte → valid GrapheRoutier."""

    def test_build_graph_from_parsed_nodes(self):
        from live_bridge.overpass_client import osm_nodes_to_points

        fake_nodes = [
            {"osm_id": 1, "lat": 48.856, "lon": 2.352, "tags": {}},
            {"osm_id": 2, "lat": 48.857, "lon": 2.353, "tags": {}},
            {"osm_id": 3, "lat": 48.858, "lon": 2.354, "tags": {}},
        ]
        points = osm_nodes_to_points(fake_nodes, id_offset=100)

        graphe = GrapheRoutier()
        depot = PointCollecte(0, 2.352, 48.856, "Depot",
                              lat=48.856, lon=2.352)
        graphe.ajouter_sommet(depot)

        for p in points:
            graphe.ajouter_sommet(p)

        # Connect all
        ids = list(graphe.sommets.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                graphe.ajouter_arete(ids[i], ids[j])

        # Verify graph is complete
        self.assertEqual(len(graphe.sommets), 4)  # depot + 3 points
        # n*(n-1) edges for bidirectional complete graph
        self.assertEqual(len(graphe.aretes), 4 * 3)

        # Verify shortest path works
        dist, path = graphe.plus_court_chemin(0, 100)
        self.assertNotEqual(dist, float('inf'))
        self.assertTrue(len(path) > 0)


if __name__ == '__main__':
    unittest.main()
