# app/api/v1/routes_encadreur.py

import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

from app.database import get_db
from app.models.memoire import Memoire, StatutMemoire
from app.models.version_memoire import VersionMemoire
from app.models.commentaire import Commentaire
from app.models.etudiant import Etudiant
from app.models.encadreur import Encadreur
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


# ══════════════════════════════════════════════
#  TABLEAU DE BORD ENCADREUR
# ══════════════════════════════════════════════

def _progression(statut: StatutMemoire) -> int:
    return {StatutMemoire.en_attente: 25, StatutMemoire.en_correction: 50,
            StatutMemoire.valide: 100, StatutMemoire.refuse: 10}.get(statut, 0)

def _echeance(memoire: Memoire) -> Optional[str]:
    if not memoire.versions:
        return None
    premiere = memoire.versions[0].depose_le
    if memoire.statut == StatutMemoire.en_correction:
        return str((premiere + timedelta(days=30)).date())
    if memoire.statut == StatutMemoire.en_attente:
        return str((premiere + timedelta(days=14)).date())
    return None


@router.get(
    "/etudiants",
    summary="Liste des étudiants de l'encadreur connecté",
    description="Retourne tous les étudiants dont les mémoires sont assignés à cet encadreur.",
)
def get_etudiants(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"])),
) -> Any:
    memoires = (
        db.query(Memoire)
        .filter(Memoire.encadreur_id == current_user.id)
        .order_by(Memoire.created_at.desc())
        .all()
    )
    result = []
    for memoire in memoires:
        etudiant = db.query(Etudiant).filter(Etudiant.id == memoire.etudiant_id).first()
        if not etudiant:
            continue
        etudiant_user = db.query(User).filter(User.id == etudiant.user_id).first()
        if not etudiant_user:
            continue
        derniere_version = memoire.versions[0] if memoire.versions else None
        result.append({
            "id":                etudiant.id,
            "nom":               etudiant_user.nom,
            "prenom":            etudiant_user.prenom,
            "titre":             memoire.titre_final or "",
            "statut":            memoire.statut.value,
            "progression":       _progression(memoire.statut),
            "chapitreActuel":    derniere_version.message_depot if derniere_version and hasattr(derniere_version, 'message_depot') else "N/A",
            "prochaineEcheance": _echeance(memoire),
            "plagiatScore":      float(memoire.score_plagiat) if memoire.score_plagiat else 0,
            "parcours":          etudiant.filiere or "",
        })
    result.sort(key=lambda x: x["prochaineEcheance"] or "9999-99-99")
    return result


@router.get(
    "/validations",
    summary="Soumissions en attente de validation",
    description="Retourne les versions de mémoires en attente de relecture pour l'encadreur.",
)
def get_validations(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["encadreur"])),
) -> Any:
    memoires_en_attente = (
        db.query(Memoire)
        .filter(
            Memoire.encadreur_id == current_user.id,
            Memoire.statut == StatutMemoire.en_attente,
        )
        .all()
    )
    result = []
    for memoire in memoires_en_attente:
        derniere_version = memoire.versions[0] if memoire.versions else None
        if not derniere_version:
            continue
        etudiant = db.query(Etudiant).filter(Etudiant.id == memoire.etudiant_id).first()
        etudiant_user = db.query(User).filter(User.id == etudiant.user_id).first() if etudiant else None
        taille_str = f"{derniere_version.taille_fichier} Ko" if hasattr(derniere_version, 'taille_fichier') and derniere_version.taille_fichier else "N/A"
        result.append({
            "id": derniere_version.id,
            "etudiant": {
                "nom":    etudiant_user.nom    if etudiant_user else "",
                "prenom": etudiant_user.prenom if etudiant_user else "",
            },
            "chapitre":      derniere_version.message_depot if hasattr(derniere_version, 'message_depot') and derniere_version.message_depot else f"Version {derniere_version.numero_version}",
            "dateDepot":     str(derniere_version.depose_le.date()) if derniere_version.depose_le else "",
            "tailleFichier": taille_str,
            "statut":        memoire.statut.value,
            "urlFichier":    f"/api/v1/memoires/{memoire.id}/versions/{derniere_version.id}/telecharger",
        })
    result.sort(key=lambda x: x["dateDepot"], reverse=True)
    return result
