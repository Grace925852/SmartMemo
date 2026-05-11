from fastapi import APIRouter, HTTPException
from app.services.ia.antiplagiat_service import analyser_plagiat
from app.services.ia.submission_service import predire_readiness
from pydantic import BaseModel

router = APIRouter(prefix="/memoires", tags=["Mémoires & IA"])

class SubmissionStats(BaseModel):
    nb_chapitres_soumis: int
    nb_chapitres_total: int
    jours_avant_soutenance: int
    nb_retours_encadreur: int
    nb_corrections_faites: int

@router.post("/{memoire_id}/analyser-plagiat")
async def verifier_plagiat(memoire_id: int, taux_similarite: float = 0.0, texte: str = ""):
    """
    Analyse le plagiat d'un mémoire.
    """
    try:
        resultat = analyser_plagiat(texte, taux_similarite)
        return {"memoire_id": memoire_id, "analyse": resultat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{memoire_id}/predire-readiness")
async def check_readiness(memoire_id: int, stats: SubmissionStats):
    """
    Prédit si l'étudiant sera prêt pour la soutenance.
    """
    resultat = predire_readiness(
        stats.nb_chapitres_soumis,
        stats.nb_chapitres_total,
        stats.jours_avant_soutenance,
        stats.nb_retours_encadreur,
        stats.nb_corrections_faites
    )
    return {"memoire_id": memoire_id, "prediction": resultat}
