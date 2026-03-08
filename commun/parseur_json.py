"""
Module de gestion des fichiers JSON (chargement et sauvegarde).
"""
import json
import os

def charger_json(chemin_fichier):
    """
    Charge les données d'un fichier JSON.
    
    Args:
        chemin_fichier (str): Chemin absolu ou relatif vers le fichier .json.
        
    Returns:
        dict/list: Le contenu du fichier JSON.
        
    Raises:
        FileNotFoundError: Si le fichier n'est pas trouvé sur le disque.
    """
    if not os.path.exists(chemin_fichier):
        raise FileNotFoundError(f"Le fichier {chemin_fichier} n'existe pas.")
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        return json.load(f)

def sauvegarder_json(donnees, chemin_fichier):
    """
    Sauvegarde des données (dictionnaire ou liste) dans un fichier JSON.
    Crée automatiquement les dossiers parents si nécessaire.
    
    Args:
        donnees: Données Python sérialisables en JSON.
        chemin_fichier (str): Chemin de destination.
    """
    os.makedirs(os.path.dirname(chemin_fichier), exist_ok=True)
    with open(chemin_fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)
