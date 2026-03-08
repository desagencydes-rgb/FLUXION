import pytest
from niveau2.src.affectateur_biparti import AffectateurBiparti
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from commun.constantes import SEUIL_DESEQUILIBRE_MAX_PCT
import statistics

def test_3_truck_3_zone_assignment():
    """a) 3 trucks assigned to 3 zones -> each truck has exactly 1 zone."""
    # Set capacity so each truck can only take one zone (1000 < 1500 < 2000)
    trucks = [Camion(i, 1500, 100, [1, 2, 3]) for i in range(1, 4)]
    zones = [Zone(i, [], 1000, 0, 0) for i in range(1, 4)]
    
    affectateur = AffectateurBiparti(trucks, zones)
    assignment = affectateur.affectation_gloutonne()
    
    # Check each truck has exactly one zone
    for t_id, z_ids in assignment.items():
        assert len(z_ids) == 1
    
    # Check all zones are covered
    assigned_zones = [z_id for z_ids in assignment.values() for z_id in z_ids]
    assert sorted(assigned_zones) == [1, 2, 3]

def test_load_balancing_deviation():
    """b) Load balancing: workload deviation < SEUIL_DESEQUILIBRE_MAX_PCT."""
    # 2 trucks, 4 zones of same volume
    trucks = [Camion(1, 5000, 100, [1, 2, 3, 4]), Camion(2, 5000, 100, [1, 2, 3, 4])]
    zones = [Zone(i, [], 1000, 0, 0) for i in range(1, 5)]
    
    affectateur = AffectateurBiparti(trucks, zones)
    assignment = affectateur.affectation_gloutonne()
    balanced = affectateur.equilibrage_charges(assignment)
    
    loads = []
    for t_id, z_ids in balanced.items():
        loads.append(sum(affectateur.zones[zid].volume_estime for zid in z_ids))
    
    mean_load = statistics.mean(loads)
    for load in loads:
        deviation_pct = abs(load - mean_load) / mean_load * 100 if mean_load > 0 else 0
        assert deviation_pct <= SEUIL_DESEQUILIBRE_MAX_PCT

def test_unbalanced_scenario():
    """c) Unbalanced scenario: 5 zones, 2 trucks -> both trucks get work."""
    # Capacity 3000 < Total 5000, so truck 1 cannot take everything
    trucks = [Camion(1, 3000, 100, list(range(1, 6))), Camion(2, 3000, 100, list(range(1, 6)))]
    zones = [Zone(i, [], 1000, 0, 0) for i in range(1, 6)]
    
    affectateur = AffectateurBiparti(trucks, zones)
    assignment = affectateur.affectation_gloutonne()
    
    assert len(assignment[1]) > 0
    assert len(assignment[2]) > 0
    assert len(assignment[1]) + len(assignment[2]) == 5

def test_edge_case_single():
    """d) Edge case: 1 truck, 1 zone -> direct assignment."""
    trucks = [Camion(1, 5000, 100, [1])]
    zones = [Zone(1, [], 1000, 0, 0)]
    
    affectateur = AffectateurBiparti(trucks, zones)
    assignment = affectateur.affectation_gloutonne()
    
    assert assignment == {1: [1]}
    assert affectateur.verifier_contraintes(assignment) is True
