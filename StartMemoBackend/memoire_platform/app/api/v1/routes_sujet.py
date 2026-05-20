from fastapi import APIRouter
from app.services.ia.approval_service import predire_approbation
from app.services.ia.recommandation_service import suggerer_sujets
from pydantic import BaseModel

router = APIRouter(prefix="/sujets", tags=["Sujets & IA"])

class SujetPropose(BaseModel):
    titre: str
    domaine: str
    niveau_etudiant: str
    mots_cles: list[str]
    nb_pages_estimees: int = 60

@router.post("/analyser")
async def analyser_sujet(sujet: SujetPropose):
    """
    Prédit l'approbation d'un sujet.
    """
    resultat = predire_approbation(
        sujet.domaine,
        sujet.niveau_etudiant,
        sujet.mots_cles,
        sujet.nb_pages_estimees
    )
    return {"sujet": sujet.titre, "validation_ia": resultat}

@router.get("/recommander")
async def recommander_sujets(domaine: str, mots_cles: str, niveau: str = "Master"):
    """
    Suggère des sujets similaires.
    """
    mots_list = mots_cles.split(",")
    resultat = suggerer_sujets(domaine, mots_list, niveau)
    return resultat
