from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Commentaire, User, VersionMemoire
from app.schemas.commentaire import CommentaireCreate, CommentaireOut

router = APIRouter(prefix="/api/v1/commentaires", tags=["Commentaires - Partie ATTA"])


def get_version_or_404(db: Session, version_id: int) -> VersionMemoire:
    version = db.query(VersionMemoire).filter(VersionMemoire.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version de mémoire introuvable")
    return version


@router.post("", response_model=CommentaireOut, status_code=status.HTTP_201_CREATED)
def ajouter_commentaire(payload: CommentaireCreate, db: Session = Depends(get_db)):
    """Ajouter un commentaire sur une version de mémoire."""
    get_version_or_404(db, payload.version_id)
    auteur = db.query(User).filter(User.id == payload.auteur_id).first()
    if not auteur:
        raise HTTPException(status_code=404, detail="Auteur introuvable")

    commentaire = Commentaire(
        version_id=payload.version_id,
        auteur_id=payload.auteur_id,
        contenu=payload.contenu,
        section=payload.section,
    )
    db.add(commentaire)
    db.commit()
    db.refresh(commentaire)
    return commentaire


@router.get("/version/{version_id}", response_model=List[CommentaireOut])
def lister_commentaires_version(version_id: int, db: Session = Depends(get_db)):
    """Lister les commentaires d'une version précise."""
    get_version_or_404(db, version_id)
    return (
        db.query(Commentaire)
        .filter(Commentaire.version_id == version_id)
        .order_by(Commentaire.created_at.desc())
        .all()
    )


@router.get("/memoire/{memoire_id}", response_model=List[CommentaireOut])
def lister_commentaires_memoire(memoire_id: int, db: Session = Depends(get_db)):
    """Lister tous les commentaires liés aux versions d'un mémoire."""
    return (
        db.query(Commentaire)
        .join(VersionMemoire, Commentaire.version_id == VersionMemoire.id)
        .filter(VersionMemoire.memoire_id == memoire_id)
        .order_by(Commentaire.created_at.desc())
        .all()
    )
