import joblib
from pathlib import Path
from functools import lru_cache

MODEL_PATH = Path("ia_models/archive/modele_archive.pkl")
VECTORIZER_PATH = Path("ia_models/archive/vectorizer_tfidf.pkl")

@lru_cache(maxsize=1)
def charger_pipeline():
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        raise FileNotFoundError("Modèle ou Vectorizer Archive introuvable")
    modele = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    return modele, vectorizer

def classifier_et_taguer(titre: str, resume: str) -> dict:
    """
    Classe un mémoire archivé et génère des tags automatiques.
    """
    try:
        modele, vectorizer = charger_pipeline()
    except Exception as e:
        return {"erreur": str(e), "status": "modèle non disponible"}
        
    texte_combine = f"{titre} {resume}"
    
    features = vectorizer.transform([texte_combine])
    domaine = modele.predict(features)[0]
    probabilites = modele.predict_proba(features)[0]
    confiance = float(max(probabilites))
    
    # Générer des tags à partir des mots les plus importants (TF-IDF)
    try:
        feature_names = vectorizer.get_feature_names_out()
        scores = features.toarray()[0]
        top_indices = scores.argsort()[-5:][::-1]
        tags = [feature_names[i] for i in top_indices if scores[i] > 0]
    except:
        tags = []
    
    return {
        "domaine_predit": domaine,
        "tags_automatiques": tags,
        "score_confiance": round(confiance * 100, 2)
    }
