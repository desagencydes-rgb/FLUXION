"""Constantes globales du projet de collecte de déchets."""

# Vitesse moyenne d'un camion en km/h
VITESSE_MOYENNE_KMH = 30.0

# Consommation carburant en litres/km
CONSOMMATION_L_PAR_KM = 0.35

# Émission CO2 en kg par litre de carburant diesel
CO2_KG_PAR_LITRE = 2.68

# Prix du carburant diesel en EUR par litre
PRIX_CARBURANT_EUR = 1.85

# Temps de service moyen par point de collecte (minutes)
TEMPS_SERVICE_MINUTES = 5.0

# Seuils de remplissage
SEUIL_AVERTISSEMENT = 70.0
SEUIL_URGENCE = 90.0
SEUIL_CRITIQUE = 95.0

# Taux de remplissage moyen par heure (% par heure)
TAUX_REMPLISSAGE_BASE = 2.0

# Limites Opérationnelles (Validées depuis projetFM.pdf)
CAPACITE_MAX_PAR_CAMION = 6000.0  # Capacité maximale autorisée par camion (en kg/L)
HEURE_DEBUT_INTERDIT_NUIT = 22    # Heure de début d'interdiction de collecte dans les zones résidentielles (22:00)
HEURE_FIN_INTERDIT_NUIT = 6       # Heure de fin d'interdiction de collecte (06:00)
TEMPS_PAUSE_OBLIGATOIRE_H = 1.0   # Durée de la pause obligatoire par jour (en heures)
DELAI_MAX_REPLANIFICATION_S = 120.0 # Délai maximal de replanification (2 minutes = 120s)
SEUIL_AMELIORATION_MO_MIN = 10.0  # Pourcentage d'amélioration minimale requise en Multi-Objectif
SEUIL_DESEQUILIBRE_MAX_PCT = 20.0 # Ecart-type max % de charge entre camions autorisé
