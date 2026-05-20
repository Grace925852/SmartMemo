import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import RoleChecker
from app.models.user import User
from app.models.jury import MembreJury
from app.models.soutenance import Soutenance
from app.models.version_memoire import VersionMemoire

router = APIRouter(prefix="/jury", tags=["Jury"])

require_jury = RoleChecker(["jury"])


# ──────────────────────────────────────────────────────────────
#  SCHÉMAS PYDANTIC
# ──────────────────────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    id: uuid.UUID
    etudiant: str
    titre: str
    date: Optional[str]
    heure: Optional[str]
    salle: Optional[str]
    statut: str
    urlMemoire: Optional[str]
    noteFinale: Optional[float]
    grille: Dict[str, Any]


# ──────────────────────────────────────────────────────────────
#  GET /jury/evaluations
# ──────────────────────────────────────────────────────────────

@router.get("/evaluations", response_model=List[EvaluationResponse])
def get_evaluations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_jury)
):
    """Soutenances assignées au membre du jury connecté pour évaluation."""
    membre_jury = (
        db.query(MembreJury)
        .filter(MembreJury.user_id == current_user.id)
        .first()
    )
    if not membre_jury:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil jury introuvable pour cet utilisateur"
        )

    soutenances = (
        db.query(Soutenance)
        .filter(
            or_(
                Soutenance.president_jury_id == membre_jury.id,
                Soutenance.examinateur_id == membre_jury.id
            )
        )
        .order_by(Soutenance.date_soutenance.asc())
        .all()
    )

    result = []
    for s in soutenances:
        memoire = s.memoire
        if not memoire:
            continue

        etudiant = memoire.etudiant
        etudiant_user = etudiant.user if etudiant else None
        etudiant_nom = (
            f"{etudiant_user.prenom} {etudiant_user.nom}"
            if etudiant_user else ""
        )

        date_str = (
            s.date_soutenance.strftime("%Y-%m-%d") if s.date_soutenance else None
        )
        heure_str = (
            s.date_soutenance.strftime("%H:%M") if s.date_soutenance else None
        )

        # Version courante du mémoire pour l'URL
        version_courante = (
            db.query(VersionMemoire)
            .filter(
                VersionMemoire.memoire_id == memoire.id,
                VersionMemoire.est_version_courante == True
            )
            .first()
        )
        url_memoire = (
            version_courante.chemin_fichier if version_courante else None
        )

        statut = "evalue" if s.note_finale is not None else "a_evaluer"

        result.append(EvaluationResponse(
            id=s.id,
            etudiant=etudiant_nom,
            titre=memoire.titre,
            date=date_str,
            heure=heure_str,
            salle=s.salle,
            statut=statut,
            urlMemoire=url_memoire,
            noteFinale=s.note_finale,
            grille={}
        ))

    return result
