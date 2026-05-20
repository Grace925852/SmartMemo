from fastapi import APIRouter
from app.services.ia.scheduler_service import planifier_soutenances
from pydantic import BaseModel
from datetime import datetime
from typing import List

router = APIRouter(prefix="/soutenances", tags=["Soutenances & IA"])

class Professeur(BaseModel):
    id: int
    nom: str

class EtudiantSoutenance(BaseModel):
    id: int
    nom: str
    jury_ids: List[int]

class PlanningRequest(BaseModel):
    etudiants: List[EtudiantSoutenance]
    salles: List[str]
    professeurs: List[Professeur]
    date_debut: datetime

@router.post("/generer-planning")
async def generer_planning(req: PlanningRequest):
    """
    Génère un planning optimisé pour les soutenances.
    """
    # Conversion pydantic vers dict pour le service
    etudiants_dict = [e.dict() for e in req.etudiants]
    profs_dict = [p.dict() for p in req.professeurs]
    
    resultat = planifier_soutenances(
        etudiants_dict,
        req.salles,
        profs_dict,
        req.date_debut
    )
    return resultat
