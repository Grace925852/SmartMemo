import pandas as pd
from pathlib import Path

ENCADREURS_DATA = Path("ia_models/assignment/encadreurs_disponibles.csv")

def proposer_affectation(
    domaine_memoire: str,
    specialites_requises: list[str]
) -> dict:
    """
    Propose le meilleur encadreur selon le domaine et la charge actuelle.
    """
    if not ENCADREURS_DATA.exists():
        return {"erreur": "Données encadreurs introuvables", "status": "indisponible"}
        
    encadreurs = pd.read_csv(ENCADREURS_DATA)
    
    # Calcul d'un score de compatibilité simple
    def calculer_score(row):
        score = 0
        specialite = str(row["specialite"]).lower()
        for spec in specialites_requises:
            if spec.lower() in specialite:
                score += 1
        # Bonus si le domaine correspond exactement
        if domaine_memoire.lower() in specialite:
            score += 0.5
        # Pénalité de charge (nb étudiants actuels)
        score -= row["nb_etudiants_actuels"] * 0.2
        return score

    encadreurs["score"] = encadreurs.apply(calculer_score, axis=1)
    
    # Trier par score
    tri_encadreurs = encadreurs.sort_values("score", ascending=False)
    
    if tri_encadreurs.empty:
        return {"erreur": "Aucun encadreur trouvé"}
        
    meilleur = tri_encadreurs.iloc[0]
    alternatives = tri_encadreurs.iloc[1:3] if len(tri_encadreurs) > 1 else pd.DataFrame()
    
    return {
        "encadreur_propose": {
            "nom": meilleur["nom"],
            "specialite": meilleur["specialite"],
            "score_compatibilite": round(float(meilleur["score"]), 2)
        },
        "alternatives": alternatives[["nom", "specialite"]].to_dict("records") if not alternatives.empty else []
    }
