import joblib
import pandas as pd
from pathlib import Path
from functools import lru_cache

SUJETS_DATA = Path("ia_models/recommandation/anciens_sujets.csv")
VECTORIZER_PATH = Path("ia_models/recommandation/vectorizer_recommandation.pkl")

@lru_cache(maxsize=1)
def charger_donnees():
    if not SUJETS_DATA.exists() or not VECTORIZER_PATH.exists():
        raise FileNotFoundError("Données ou Vectorizer Recommandation introuvable")
    df = pd.read_csv(SUJETS_DATA)
    vectorizer = joblib.load(VECTORIZER_PATH)
    return df, vectorizer

def suggerer_sujets(
    domaine: str,
    mots_cles: list[str],
    niveau: str,
    top_n: int = 5
) -> dict:
    """
    Suggère des sujets de mémoire similaires à des projets antérieurs.
    """
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        df, vectorizer = charger_donnees()
    except Exception as e:
        return {"erreur": str(e), "suggestions": []}
    
    requete = f"{domaine} {' '.join(mots_cles)}"
    try:
        vecteur_requete = vectorizer.transform([requete])
        # On suppose que le vectorizer a été entraîné sur une colonne 'texte_complet'
        # Ici on recalcule pour la démo si besoin, mais idéalement c'est pré-calculé
        vecteurs_sujets = vectorizer.transform(df["titre"].astype(str) + " " + df["description"].astype(str))
        
        scores = cosine_similarity(vecteur_requete, vecteurs_sujets)[0]
        df["score"] = scores
        
        top_sujets = df.sort_values("score", ascending=False).head(top_n)
        
        return {
            "suggestions": [
                {
                    "titre": row["titre"],
                    "domaine": row["domaine"],
                    "annee": row.get("annee", "N/A"),
                    "score_pertinence": round(float(row["score"]) * 100, 2)
                }
                for _, row in top_sujets.iterrows() if row["score"] > 0
            ]
        }
    except Exception as e:
        return {"erreur": f"Erreur lors du calcul : {str(e)}", "suggestions": []}
