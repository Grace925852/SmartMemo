import joblib
import numpy as np
from pathlib import Path
from functools import lru_cache

MODEL_PATH = Path("ia_models/approval/modele_approval.pkl")
ENCODER_PATH = Path("ia_models/approval/encodeur_domaine.pkl")

@lru_cache(maxsize=1)
def charger_modele():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modèle introuvable : {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

@lru_cache(maxsize=1)
def charger_encodeur():
    if not ENCODER_PATH.exists():
        raise FileNotFoundError(f"Encodeur introuvable : {ENCODER_PATH}")
    return joblib.load(ENCODER_PATH)

def predire_approbation(
    domaine: str,
    niveau_etudiant: str,
    mots_cles: list[str],
    nb_pages_estimees: int
) -> dict:
    """
    Prédit la probabilité d'approbation d'un sujet de mémoire.
    """
    try:
        modele = charger_modele()
        encodeur = charger_encodeur()
    except Exception as e:
        return {"erreur": str(e), "status": "modèle non disponible"}
    
    try:
        domaine_encode = encodeur.transform([domaine])[0]
    except:
        domaine_encode = 0 # Fallback
        
    niveau_encode = {"Licence": 0, "Master": 1, "Doctorat": 2}.get(niveau_etudiant, 1)
    nb_mots_cles = len(mots_cles)
    
    features = np.array([[domaine_encode, niveau_encode, nb_mots_cles, nb_pages_estimees]])
    prediction = modele.predict(features)[0]
    probabilite = modele.predict_proba(features)[0][1]  # Probabilité classe "Approuvé"
    
    recommandations = []
    if probabilite < 0.5:
        recommandations.append("Préciser davantage la problématique.")
        recommandations.append("Ajouter des mots-clés spécifiques au domaine.")
    else:
        recommandations.append("Sujet solide. Prêt pour soumission.")
    
    return {
        "approuve": bool(prediction),
        "probabilite": round(float(probabilite) * 100, 2),
        "recommandations": recommandations
    }
