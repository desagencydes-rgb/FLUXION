"""
Module d'utilitaires mathématiques pour le projet de collecte de déchets.
"""
import math

def distance_euclidienne(p1, p2):
    """
    Calcule la distance euclidienne entre deux points dans un plan 2D.
    
    Args:
        p1: Objet possédant des attributs x et y.
        p2: Objet possédant des attributs x et y.
        
    Returns:
        float: La distance géométrique entre p1 et p2.
    """
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
