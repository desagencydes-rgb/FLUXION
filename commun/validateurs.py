"""Validateurs pour les données d'entrée du projet."""

def valider_point(data: dict) -> bool:
    """Vérifie qu'un dict de point contient id, x, y numériques."""
    required = ["id", "x", "y"]
    for key in required:
        if key not in data:
            raise ValueError(f"Champ manquant: {key}")
        if not isinstance(data[key], (int, float)):
            raise TypeError(f"{key} doit être numérique, reçu: {type(data[key])}")
    return True

def valider_camion(data: dict) -> bool:
    """Vérifie qu'un dict camion contient id, capacite > 0, cout_fixe >= 0."""
    required = ["id", "capacite", "cout_fixe"]
    for key in required:
        if key not in data:
            raise ValueError(f"Champ manquant: {key}")
    if data["capacite"] <= 0:
        raise ValueError("capacite doit être > 0")
    if data["cout_fixe"] < 0:
        raise ValueError("cout_fixe doit être >= 0")
    return True

def valider_zone(data: dict) -> bool:
    """Vérifie qu'un dict zone contient id, centre avec x/y."""
    if "id" not in data:
        raise ValueError("Champ manquant: id")
    centre = data.get("centre", {})
    if "x" not in centre or "y" not in centre:
        raise ValueError("Zone doit avoir centre.x et centre.y")
    return True
