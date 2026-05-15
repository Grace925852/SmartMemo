# app/api/v1/routes_encadreur.py

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.memoire import Memoire, StatutMemoire
from app.models.version_memoire import VersionMemoire
from app.models.commentaire import Commentaire
from app.api.deps import RoleChecker, get_current_active_user
from app.models.user import User

# ─────────────────────────────────────────────
# INITIALISATION DU ROUTER
# ─────────────────────────────────────────────
router = APIRouter(
    prefix="/encadreur",
    tags=["Encadreur"]
)

# ══════════════════════════════════════════════
#  SCHÉMAS PYDANTIC
# ══════════════════════════════════════════════

class CommentaireCreate(BaseModel):
    contenu: str
    section: Optional[str] = None

class CommentaireResponse(BaseModel):
    id: uuid.UUID
    contenu: str
    section: Optional[str]
    created_at: datetime
    auteur_id: uuid.UUID
    
    class Config:
        from_attributes = True

class ValidationResponse(BaseModel):
    message: str
    statut: str
    memoire_id: uuid.UUID

class RefusResponse(BaseModel):
    message: str
    statut: str
    memoire_id: uuid.UUID
    motif: Optional[str] = None

class CorrectionResponse(BaseModel):
    message: str
    statut: str
    memoire_id: uuid.UUID

class VersionInfo(BaseModel):
    id: uuid.UUID
    numero_version: int
    nom_fichier: str
    statut: str
    depose_le: datetime
    
    class Config:
        from_attributes = True

class SuiviMemoire(BaseModel):
    id: uuid.UUID
    titre_final: Optional[str]
    statut: str
    created_at: datetime
    updated_at: datetime
    versions: List[VersionInfo] = []
    commentaires: List[CommentaireResponse] = []
    
    class Config:
        from_attributes = True

# ══════════════════════════════════════════════
#  ROUTES VALIDATION / REFUS / CORRECTION
# ══════════════════════════════════════════════

@router.put("/memoires/{memoire_id}/valider", response_model=ValidationResponse)
def valider_memoire(
    memoire_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"]))
):
    """
    Valider un mémoire.
    Change le statut du mémoire à 'valide'.
    """
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mémoire non trouvé"
        )
    
    memoire.statut = StatutMemoire.valide
    db.commit()
    
    return ValidationResponse(
        message="Mémoire validé avec succès",
        statut="valide",
        memoire_id=memoire_id
    )

@router.put("/memoires/{memoire_id}/refuser", response_model=RefusResponse)
def refuser_memoire(
    memoire_id: uuid.UUID,
    motif: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"]))
):
    """
    Refuser un mémoire.
    Change le statut du mémoire à 'refuse'.
    """
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mémoire non trouvé"
        )
    
    memoire.statut = StatutMemoire.refuse
    db.commit()
    
    return RefusResponse(
        message="Mémoire refusé",
        statut="refuse",
        memoire_id=memoire_id,
        motif=motif
    )

@router.put("/memoires/{memoire_id}/correction", response_model=CorrectionResponse)
def mettre_en_correction(
    memoire_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"]))
):
    """
    Mettre un mémoire en correction.
    Change le statut du mémoire à 'en_correction'.
    """
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mémoire non trouvé"
        )
    
    memoire.statut = StatutMemoire.en_correction
    db.commit()
    
    return CorrectionResponse(
        message="Mémoire mis en correction",
        statut="en_correction",
        memoire_id=memoire_id
    )

# ══════════════════════════════════════════════
#  ROUTES COMMENTAIRES
# ══════════════════════════════════════════════

@router.post("/memoires/{memoire_id}/commentaires", response_model=CommentaireResponse)
def ajouter_commentaire(
    memoire_id: uuid.UUID,
    commentaire: CommentaireCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"]))
):
    """
    Ajouter un commentaire sur un mémoire.
    Le commentaire est lié à la dernière version du mémoire.
    """
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mémoire non trouvé"
        )
    
    # Récupérer la dernière version du mémoire
    derniere_version = db.query(VersionMemoire).filter(
        VersionMemoire.memoire_id == memoire_id
    ).order_by(VersionMemoire.numero_version.desc()).first()
    
    if not derniere_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune version trouvée pour ce mémoire"
        )
    
    nouveau_commentaire = Commentaire(
        version_id=derniere_version.id,
        auteur_id=current_user.id,
        contenu=commentaire.contenu,
        section=commentaire.section
    )
    
    db.add(nouveau_commentaire)
    db.commit()
    db.refresh(nouveau_commentaire)
    
    return nouveau_commentaire

# ══════════════════════════════════════════════
#  ROUTES SUIVI
# ══════════════════════════════════════════════

@router.get("/memoires/{memoire_id}/suivi", response_model=SuiviMemoire)
def voir_suivi(
    memoire_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"]))
):
    """
    Voir le suivi complet d'un mémoire.
    Retourne le statut actuel, l'historique des versions et les commentaires.
    """
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mémoire non trouvé"
        )
    
    # Récupérer toutes les versions
    versions = db.query(VersionMemoire).filter(
        VersionMemoire.memoire_id == memoire_id
    ).order_by(VersionMemoire.numero_version.asc()).all()
    
    # Récupérer tous les commentaires
    commentaires = []
    for version in versions:
        commentaires_version = db.query(Commentaire).filter(
            Commentaire.version_id == version.id
        ).all()
        commentaires.extend(commentaires_version)
    
    return SuiviMemoire(
        id=memoire.id,
        titre_final=memoire.titre_final,
        statut=memoire.statut.value,
        created_at=memoire.created_at,
        updated_at=memoire.updated_at,
        versions=[VersionInfo(
            id=v.id,
            numero_version=v.numero_version,
            nom_fichier=v.nom_fichier,
            statut=v.statut.value,
            depose_le=v.depose_le
        ) for v in versions],
        commentaires=[CommentaireResponse(
            id=c.id,
            contenu=c.contenu,
            section=c.section,
            created_at=c.created_at,
            auteur_id=c.auteur_id
        ) for c in commentaires]
    )
