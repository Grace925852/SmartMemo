import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.database import get_db
from app.models.archive import Archive

router = APIRouter(prefix="/archive", tags=["Archive"])


# ──────────────────────────────────────────────────────────────
#  SCHÉMAS PYDANTIC
# ──────────────────────────────────────────────────────────────

class ArchiveSearchResponse(BaseModel):
    id: uuid.UUID
    titre: str
    auteur: str
    annee: Optional[str]
    domaine: Optional[str]
    filiere: Optional[str]
    tags: List[str]
    telechargements: int
    resume: Optional[str]
    urlFichier: Optional[str]


# ──────────────────────────────────────────────────────────────
#  GET /archive/search
# ──────────────────────────────────────────────────────────────

@router.get("/search", response_model=List[ArchiveSearchResponse])
def search_archives(
    q: Optional[str] = Query(None, description="Terme de recherche (titre, résumé, tags)"),
    domaine: Optional[str] = Query(None, description="Filtrer par domaine académique"),
    annee: Optional[str] = Query(None, description="Filtrer par année (ex: 2026)"),
    filiere: Optional[str] = Query(None, description="Filtrer par filière"),
    db: Session = Depends(get_db)
):
    """Recherche dans l'archive publique des mémoires validés."""
    query = db.query(Archive)

    if domaine:
        query = query.filter(Archive.domaine.ilike(f"%{domaine}%"))

    if annee:
        try:
            annee_int = int(annee)
            query = query.filter(Archive.annee_soutenance == annee_int)
        except ValueError:
            pass

    if filiere:
        query = query.filter(Archive.filiere.ilike(f"%{filiere}%"))

    if q:
        query = query.filter(
            or_(
                Archive.titre.ilike(f"%{q}%"),
                Archive.resume.ilike(f"%{q}%"),
                Archive.mots_cles.ilike(f"%{q}%")
            )
        )

    archives = query.all()

    result = []
    for a in archives:
        tags = [
            t.strip()
            for t in (a.mots_cles or "").split(",")
            if t.strip()
        ]

        result.append(ArchiveSearchResponse(
            id=a.id,
            titre=a.titre or "",
            auteur=a.auteur_nom or "",
            annee=str(a.annee_soutenance) if a.annee_soutenance else None,
            domaine=a.domaine,
            filiere=a.filiere,
            tags=tags,
            telechargements=0,
            resume=a.resume,
            urlFichier=a.chemin_fichier
        ))

    return result
