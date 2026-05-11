import joblib
import numpy as np
from pathlib import Path
from functools import lru_cache

MODEL_PATH = Path("ia_models/submission/modele_submission.pkl")

@lru_cache(maxsize=1)
def charger_modele():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modèle Submission introuvable : {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def predire_readiness(
    nb_chapitres_soumis: int,
    nb_chapitres_total: int,
    jours_avant_soutenance: int,
    nb_retours_encadreur: int,
    nb_corrections_faites: int
) -> dict:
    """
    Prédit si l'étudiant sera prêt à temps pour soutenir.
    """
    try:
        modele = charger_modele()
    except Exception as e:
        return {"erreur": str(e), "probabilite": 0, "pret_a_temps": False}
        
    taux_avancement = nb_chapitres_soumis / max(nb_chapitres_total, 1)
    taux_corrections = nb_corrections_faites / max(nb_retours_encadreur, 1)
    
    features = np.array([[
        taux_avancement,
        jours_avant_soutenance,
        nb_retours_encadreur,
        taux_corrections
    ]])
    
    prediction = modele.predict(features)[0]
    probabilite = modele.predict_proba(features)[0][1]
    
    alerte = None
    conseil = ""
    
    if jours_avant_soutenance < 30 and taux_avancement < 0.7:
        alerte = "⚠️ CRITIQUE : Retard important détecté."
        conseil = "Planifier une session intensive avec l'encadreur immédiatement."
    elif probabilite < 0.5:
        alerte = "⚡ Attention : Risque de retard."
        conseil = "Accélérer les soumissions de chapitres."
    else:
        conseil = "Bon rythme d'avancement. Continuer ainsi."
    
    return {
        "pret_a_temps": bool(prediction),
        "probabilite": round(float(probabilite) * 100, 2),
        "taux_avancement": round(taux_avancement * 100, 1),
        "alerte": alerte,
        "conseil": conseil
    }
