import pytest
from datetime import datetime
from niveau3.src.planificateur_triparti import PlanificateurTriparti
from niveau3.src.creneau_horaire import CreneauHoraire
from niveau3.src.contrainte_temporelle import ContrainteTemporelle
from niveau2.src.affectateur_biparti import AffectateurBiparti
from niveau2.src.camion import Camion
from niveau2.src.zone import Zone
from commun.constantes import TEMPS_PAUSE_OBLIGATOIRE_H

@pytest.fixture
def base_setup():
    trucks = [Camion(1, 5000, 100, [1, 2])]
    zones = [Zone(1, [], 1000, 0, 0), Zone(2, [], 1000, 1, 1)]
    affectateur = AffectateurBiparti(trucks, zones)
    return trucks, zones, affectateur

def test_night_ban_constraint():
    """a) Night ban: no collections scheduled between 22:00 and 06:00."""
    # We'll mark Zone 1 as having a night ban restriction
    # In niveau3/src/contrainte_temporelle.py, the check is based on zones_interdites_nuit set
    trucks, zones, affectateur = [Camion(1, 10000, 100, [1])], [Zone(1, [], 100, 0, 0)], AffectateurBiparti([Camion(1, 10000, 100, [1])], [Zone(1, [], 100, 0, 0)])
    
    contraintes = ContrainteTemporelle()
    contraintes.zones_interdites_nuit.add(1)
    
    # Create two slots: one day, one night
    day_slot = CreneauHoraire(1, "10:00", "11:00", "Lundi")
    night_slot = CreneauHoraire(2, "23:00", "00:00", "Lundi")
    
    assert contraintes.est_realisable(1, 1, day_slot) is True
    assert contraintes.est_realisable(1, 1, night_slot) is False

def test_driver_break_at_least_1h():
    """b) Driver breaks: at least 1 hour break per day."""
    contraintes = ContrainteTemporelle()
    # Add a 1h pause at 12:00
    contraintes.ajouter_pause_camion(1, "12:00", TEMPS_PAUSE_OBLIGATOIRE_H)
    
    overlap_slot = CreneauHoraire(1, "12:30", "13:30", "Lundi")
    ok_slot = CreneauHoraire(2, "14:00", "15:00", "Lundi")
    
    assert contraintes.est_realisable(1, 1, overlap_slot) is False
    assert contraintes.est_realisable(1, 1, ok_slot) is True

def test_conflict_free_scheduling():
    """c) Conflict-free: no two trucks assigned to same zone at same time (implicit in current level3 logic)."""
    # Current implementation ensures one camion per slot/zone via generer_plan_optimal
    trucks = [Camion(1, 5000, 100, [1]), Camion(2, 5000, 100, [1])]
    zones = [Zone(1, [], 100, 0, 0)]
    affectateur = AffectateurBiparti(trucks, zones)
    
    contraintes = ContrainteTemporelle()
    slost = [CreneauHoraire(1, "08:00", "09:00", "Lundi")]
    
    planificateur = PlanificateurTriparti(affectateur, contraintes, slost)
    plan = planificateur.generer_plan_optimal(horizon_jours=1)
    
    # For one zone and one slot, only one truck should be scheduled
    hits = plan["Lundi"]
    assert len(hits) == 1
    assert hits[0]["camion_id"] in [1, 2]

def test_full_coverage_24h():
    """d) Full coverage: all zones visited at least once (if capacity/time permits)."""
    trucks = [Camion(1, 10000, 100, [1, 2])]
    zones = [Zone(1, [], 100, 0, 0), Zone(2, [], 100, 1, 1)]
    affectateur = AffectateurBiparti(trucks, zones)
    
    # 2 zones need 2 slots for 1 truck
    slots = [
        CreneauHoraire(1, "08:00", "09:00", "Lundi"),
        CreneauHoraire(2, "09:00", "10:00", "Lundi")
    ]
    
    planificateur = PlanificateurTriparti(affectateur, contraintes=ContrainteTemporelle(), creneaux=slots)
    plan = planificateur.generer_plan_optimal(1)
    

