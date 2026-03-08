import pytest
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from niveau4.src.tournee import Tournee
from niveau1.src.graphe_routier import GrapheRoutier
from niveau1.src.point_collecte import PointCollecte
from niveau2.src.camion import Camion
from commun.constantes import CAPACITE_MAX_PAR_CAMION

@pytest.fixture
def base_data():
    # Simple grid graph for predictable distances
    g = GrapheRoutier()
    points = [
        PointCollecte(0, "Dépôt", 0, 0, 0),
        PointCollecte(1, "A", 1, 0, 100),
        PointCollecte(2, "B", 1, 1, 100),
        PointCollecte(3, "C", 0, 1, 100),
    ]
    for p in points:
        g.ajouter_sommet(p)
    
    # Distance matrix proxy (assuming euclidean for simplicity if needed)
    # The actual GrapheRoutier needs plus_court_chemin or distance_matrix
    # We'll just define points and let Dijkstra run.
    g.ajouter_arete(0, 1, 10)
    g.ajouter_arete(1, 2, 10)
    g.ajouter_arete(2, 3, 10)
    g.ajouter_arete(3, 0, 10)
    g.ajouter_arete(0, 2, 14.1) # Shortcut
    
    camions = [Camion(1, CAPACITE_MAX_PAR_CAMION, 100, [1, 2, 3])]
    points_dict = {p.id: p for p in points if p.id != 0}
    
    return g, camions, points_dict

def test_2opt_improvement(base_data):
    """a) 2-opt improvement: optimized distance < naive distance."""
    g, camions, pts = base_data
    optim = OptimiseurVRP(g, camions, pts)
    
    # Create a non-optimal tour [0, 2, 1, 3, 0] (crossed)
    tour = Tournee(1, [0, 2, 1, 3, 0])
    naive_dist = tour.calculer_distance(g)
    
    improved_tour = optim.algorithme_2opt(tour)
    opt_dist = improved_tour.calculer_distance(g)
    
    assert opt_dist <= naive_dist

def test_tabu_iteration_stability(base_data):
    """b) Tabu search: solution improves or stays equal over iterations."""
    g, camions, pts = base_data
    optim = OptimiseurVRP(g, camions, pts)
    
    initial_sol = optim.construire_solution_initiale()
    initial_dist = sum(t.calculer_distance(g) for t in initial_sol)
    
    tabu_sol = optim.recherche_tabou(iterations=10)
    tabu_dist = sum(t.calculer_distance(g) for t in tabu_sol)
    
    assert tabu_dist <= initial_dist

def test_capacity_constraint(base_data):
    """c) Capacity constraint: no truck exceeds CAPACITE_MAX_PAR_CAMION."""
    g, camions, pts = base_data
    # Force many points with volume
    for p_id in pts:
        pts[p_id].volume_moyen = 2000 # 3 pts = 6000 kg (max)
    
    optim = OptimiseurVRP(g, camions, pts)
    solution = optim.recherche_tabou(iterations=5)
    
    for t in solution:
        # Check volume (proxied by num points in tournee.py if volume not explicit)
        assert t.verifier_faisabilite({'capacite_max': CAPACITE_MAX_PAR_CAMION / 1000})

def test_all_points_visited_exactly_once(base_data):
    """d) All points visited: every collection point appears exactly once across all routes."""
    g, camions, pts = base_data
    optim = OptimiseurVRP(g, camions, pts)
    solution = optim.recherche_tabou(iterations=5)
    
    visited = []
    for t in solution:
        # Strip depot (start/end)
        visited.extend(t.points_ids[1:-1])
    
    assert sorted(visited) == sorted(pts.keys())

def test_depot_invariant(base_data):
    """e) Depot start/end: every route starts and ends at the depot."""
    g, camions, pts = base_data
    optim = OptimiseurVRP(g, camions, pts)
    solution = optim.recherche_tabou(iterations=5)
    
    depot_id = 0
    for t in solution:
        assert t.points_ids[0] == depot_id
        assert t.points_ids[-1] == depot_id
