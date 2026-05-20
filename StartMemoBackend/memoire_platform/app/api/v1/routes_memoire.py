# app/api/v1/routes_memoire.py

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel

from app.database import get_db
from app.schemas.memoire_schema import (
    MemoireCreer,
    MemoireReponse,
    MemoireResume,
    VersionMemoireReponse,
)
from app.models.memoire import Memoire, StatutMemoire
from app.models.commentaire import Commentaire
from app.models.version_memoire import VersionMemoire as VersionMemoireModel
import app.services.memoire_service as service
from app.services.ia.antiplagiat_service import analyser_plagiat
from app.services.ia.submission_service import predire_readiness
from app.api.deps import RoleChecker, get_current_active_user
from app.models.user import User

# ─────────────────────────────────────────────
# INITIALISATION DU ROUTER
# ─────────────────────────────────────────────
router = APIRouter(
    prefix="/memoires",
    tags=["Mémoires"]
)

# ══════════════════════════════════════════════
#  ROUTES DÉPÔT & GESTION (Core)
# ══════════════════════════════════════════════

@router.post(
    "/",
    response_model=MemoireReponse,
    status_code=201,
    summary="Déposer un nouveau mémoire",
    description="""
    L'étudiant dépose son mémoire pour la première fois.  
    Requiert un fichier PDF + les métadonnées du mémoire.  
    Crée automatiquement la **version 1** et place le statut à **en_attente**.
    """
)
async def deposer_memoire(
    titre: str = Form(..., description="Titre du mémoire"),
    description: Optional[str] = Form(None, description="Résumé ou description"),
    domaine: Optional[str] = Form(None, description="Ex: Informatique, Droit"),
    annee_academique: Optional[str] = Form(None, description="Ex: 2024-2025"),
    message_depot: Optional[str] = Form(None, description="Message accompagnant le dépôt"),
    fichier: UploadFile = File(..., description="Fichier PDF du mémoire (max 20 Mo)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["etudiant", "admin"]))
):
    donnees = MemoireCreer(
        titre=titre,
        description=description,
        domaine=domaine,
        annee_academique=annee_academique,
        message_depot=message_depot
    )
    return service.creer_memoire_et_deposer(db, donnees, fichier, current_user.id)


@router.post(
    "/{memoire_id}/versions",
    response_model=VersionMemoireReponse,
    status_code=201,
    summary="Déposer une nouvelle version d'un mémoire existant",
    description="""
    L'étudiant soumet une nouvelle version après correction.  
    Le numéro de version est **incrémenté automatiquement**.  
    Le statut du mémoire repasse à **en_attente** pour que l'encadreur relise.
    """
)
async def deposer_nouvelle_version(
    memoire_id: int,
    message_depot: Optional[str] = Form(None, description="Description des modifications apportées"),
    fichier: UploadFile = File(..., description="Nouveau fichier PDF"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["etudiant"]))
):
    return service.deposer_nouvelle_version(db, memoire_id, fichier, current_user.id, message_depot)


@router.get(
    "/{memoire_id}",
    response_model=MemoireReponse,
    summary="Obtenir un mémoire avec toutes ses versions"
)
def obtenir_memoire(
    memoire_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "encadreur", "etudiant", "jury"]))
):
    return service.obtenir_memoire_par_id(db, memoire_id)


@router.get(
    "/etudiant/{etudiant_id}",
    response_model=List[MemoireResume],
    summary="Lister tous les mémoires d'un étudiant"
)
def lister_memoires_etudiant(
    etudiant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "encadreur", "etudiant"]))
):
    return service.lister_memoires_etudiant(db, etudiant_id)


@router.get(
    "/{memoire_id}/versions",
    response_model=List[VersionMemoireReponse],
    summary="Voir l'historique complet des dépôts d'un mémoire"
)
def historique_versions(
    memoire_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["etudiant", "encadreur", "admin", "jury"]))
):
    return service.lister_historique_versions(db, memoire_id)


@router.get(
    "/{memoire_id}/versions/{version_id}/telecharger",
    summary="Télécharger le fichier PDF d'une version spécifique"
)
def telecharger_version(
    memoire_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["etudiant", "encadreur", "admin", "jury"]))
):
    from app.models.version_memoire import VersionMemoire
    
    version = db.query(VersionMemoire).filter(
        VersionMemoire.id == version_id,
        VersionMemoire.memoire_id == memoire_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version introuvable.")
    
    chemin = Path(version.chemin_fichier)
    if not chemin.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur.")
    
    return FileResponse(
        path=str(chemin),
        filename=version.nom_fichier_original,
        media_type="application/pdf"
    )


# ══════════════════════════════════════════════
#  ROUTES IA (Analyse & Prédiction)
# ══════════════════════════════════════════════

class SubmissionStats(BaseModel):
    nb_chapitres_soumis: int
    nb_chapitres_total: int
    jours_avant_soutenance: int
    nb_retours_encadreur: int
    nb_corrections_faites: int

@router.post("/{memoire_id}/analyser-plagiat", tags=["IA"])
async def verifier_plagiat(memoire_id: int, taux_similarite: float = 0.0, texte: str = ""):
    """Analyse le plagiat d'un mémoire."""
    try:
        resultat = analyser_plagiat(texte, taux_similarite)
        return {"memoire_id": memoire_id, "analyse": resultat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{memoire_id}/predire-readiness", tags=["IA"])
async def check_readiness(memoire_id: int, stats: SubmissionStats):
    """Prédit si l'étudiant sera prêt pour la soutenance."""
    resultat = predire_readiness(
        stats.nb_chapitres_soumis,
        stats.nb_chapitres_total,
        stats.jours_avant_soutenance,
        stats.nb_retours_encadreur,
        stats.nb_corrections_faites
    )
    return {"memoire_id": memoire_id, "prediction": resultat}


# ══════════════════════════════════════════════
#  ACTIONS DE VALIDATION (Encadreur)
# ══════════════════════════════════════════════

class ValiderCorps(BaseModel):
    commentaire: Optional[str] = None


class CommenterCorps(BaseModel):
    contenu: str
    section: Optional[str] = None
    version_id: Optional[int] = None


class RejeterCorps(BaseModel):
    motif: str
    type_rejet: str  # "refuse" | "en_correction"


def _get_memoire_encadreur(memoire_id: int, encadreur_user_id, db: Session) -> Memoire:
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mémoire introuvable.")
    if memoire.encadreur_id != encadreur_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'êtes pas l'encadreur de ce mémoire.")
    return memoire


@router.post(
    "/{memoire_id}/valider",
    summary="Valider un mémoire (encadreur)",
    description="L'encadreur valide le mémoire et peut laisser un commentaire de validation.",
    tags=["Actions encadreur"],
)
def valider_memoire(
    memoire_id: int,
    corps: ValiderCorps,
    current_user: User = Depends(RoleChecker(["encadreur"])),
    db: Session = Depends(get_db),
):
    memoire = _get_memoire_encadreur(memoire_id, current_user.id, db)

    if memoire.statut == StatutMemoire.valide:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le mémoire est déjà validé.")

    memoire.statut = StatutMemoire.valide
    db.add(memoire)

    if corps.commentaire:
        derniere_version = memoire.versions[0] if memoire.versions else None
        commentaire = Commentaire(
            version_id=derniere_version.id if derniere_version else None,
            auteur_id=current_user.id,
            contenu=corps.commentaire,
            section="validation",
            type="validation",
        )
        db.add(commentaire)

    db.commit()
    db.refresh(memoire)

    return {
        "memoire_id": memoire.id,
        "statut":     memoire.statut.value,
        "message":    "Mémoire validé avec succès.",
    }


@router.post(
    "/{memoire_id}/commenter",
    status_code=status.HTTP_201_CREATED,
    summary="Commenter une version (encadreur)",
    description="L'encadreur ajoute des retours sur une version sans changer le statut du mémoire.",
    tags=["Actions encadreur"],
)
def commenter_memoire(
    memoire_id: int,
    corps: CommenterCorps,
    current_user: User = Depends(RoleChecker(["encadreur"])),
    db: Session = Depends(get_db),
):
    memoire = _get_memoire_encadreur(memoire_id, current_user.id, db)

    # Résoudre la version cible
    version_id = corps.version_id
    if version_id is None and memoire.versions:
        version_id = memoire.versions[0].id

    if version_id:
        version_existe = db.query(VersionMemoireModel).filter(
            VersionMemoireModel.id == version_id,
            VersionMemoireModel.memoire_id == memoire_id,
        ).first()
        if not version_existe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable.")

    commentaire = Commentaire(
        version_id=version_id,
        auteur_id=current_user.id,
        contenu=corps.contenu,
        section=corps.section,
        type="commentaire",
    )
    db.add(commentaire)
    db.commit()
    db.refresh(commentaire)

    return {
        "id":         commentaire.id,
        "memoire_id": memoire_id,
        "version_id": commentaire.version_id,
        "contenu":    commentaire.contenu,
        "section":    commentaire.section,
        "cree_le":    commentaire.created_at.isoformat() if commentaire.created_at else None,
    }


@router.post(
    "/{memoire_id}/rejeter",
    summary="Rejeter un mémoire (encadreur)",
    description="L'encadreur rejette ou demande des corrections. Le motif est obligatoire.",
    tags=["Actions encadreur"],
)
def rejeter_memoire(
    memoire_id: int,
    corps: RejeterCorps,
    current_user: User = Depends(RoleChecker(["encadreur"])),
    db: Session = Depends(get_db),
):
    if not corps.motif or not corps.motif.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le motif est obligatoire.")

    if corps.type_rejet not in ("refuse", "en_correction"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type_rejet doit être 'refuse' ou 'en_correction'.")

    memoire = _get_memoire_encadreur(memoire_id, current_user.id, db)

    if memoire.statut == StatutMemoire.valide:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de rejeter un mémoire déjà validé.")

    nouveau_statut = StatutMemoire.refuse if corps.type_rejet == "refuse" else StatutMemoire.en_correction
    memoire.statut = nouveau_statut
    db.add(memoire)

    derniere_version = memoire.versions[0] if memoire.versions else None
    commentaire = Commentaire(
        version_id=derniere_version.id if derniere_version else None,
        auteur_id=current_user.id,
        contenu=corps.motif,
        section="rejet",
        type="rejet",
    )
    db.add(commentaire)
    db.commit()
    db.refresh(memoire)

    return {
        "memoire_id": memoire.id,
        "statut":     memoire.statut.value,
        "motif":      corps.motif,
        "message":    "Décision enregistrée.",
    }
