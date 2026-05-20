import joblib
import numpy as np
from pathlib import Path
from functools import lru_cache

# Chemin relatif depuis le point d'exécution (la racine memoire_platform)
MODEL_PATH = Path("ia_models/antiplagiat/modele_antiplagiat.pkl")

@lru_cache(maxsize=1)
def charger_modele():
    """Charge le modèle une seule fois et le met en cache mémoire."""
    if not MODEL_PATH.exists():
        # Fallback pour le développement : essayer de charger depuis ia_models à la racine si pas trouvé
        if Path("ia_models/antiplagiat/modele_antiplagiat.pkl").exists():
             return joblib.load(Path("ia_models/antiplagiat/modele_antiplagiat.pkl"))
        raise FileNotFoundError(
            f"Modèle introuvable : {MODEL_PATH}. "
            "Lancez d'abord scripts_ia/antiplagiat/etape3_entrainer_modele.py"
        )
    return joblib.load(MODEL_PATH)

def analyser_plagiat(texte_soumis: str, taux_similarite: float) -> dict:
    """
    Prédit la catégorie de plagiat d'un texte.
    
    Args:
        texte_soumis: Contenu textuel du mémoire
        taux_similarite: Score de similarité calculé (0.0 à 1.0)
    
    Returns:
        dict avec 'categorie', 'confiance', 'details'
    """
    try:
        modele = charger_modele()
    except Exception as e:
        return {"erreur": str(e), "status": "modèle non disponible"}
    
    # Feature engineering simplifié (doit correspondre à l'entraînement)
    mots = texte_soumis.split()
    mots_uniques = set(mots)
    
    features = np.array([[
        taux_similarite,
        len(mots),              # Nombre de mots
        len(mots_uniques),      # Vocabulaire unique
    ]])
    
    prediction = modele.predict(features)[0]
    probabilites = modele.predict_proba(features)[0]
    confiance = float(max(probabilites))
    
    return {
        "categorie": prediction,   # "Original", "Similaire", "Plagiat Partiel", "Plagiat Total"
        "confiance": round(confiance * 100, 2),
        "taux_similarite": taux_similarite,
        "details": {
            classe: round(float(prob) * 100, 2)
            for classe, prob in zip(modele.classes_, probabilites)
        }
    }
