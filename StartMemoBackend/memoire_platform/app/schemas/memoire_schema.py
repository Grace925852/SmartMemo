# app/schemas/memoire_schema.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.memoire import StatutMemoire


# ─────────────────────────────────────────────
# SCHÉMAS D'ENTRÉE (ce que l'API reçoit)
# ─────────────────────────────────────────────

class MemoireCreer(BaseModel):
    """
    Données envoyées par l'étudiant pour créer un nouveau mémoire.
    Le fichier PDF est envoyé séparément (multipart/form-data).
    """
    titre: str = Field(..., min_length=5, max_length=300, example="Impact de l'IA sur l'éducation en Afrique")
    description: Optional[str] = Field(None, example="Ce mémoire analyse...")
    domaine: Optional[str] = Field(None, example="Informatique")
    annee_academique: Optional[str] = Field(None, example="2024-2025")
    message_depot: Optional[str] = Field(None, example="Première version complète")


class MemoireMettreAJour(BaseModel):
    """
    Données optionnelles pour modifier les infos d'un mémoire existant.
    Tous les champs sont optionnels (PATCH).
    """
    titre: Optional[str] = Field(None, min_length=5, max_length=300)
    description: Optional[str] = None
    domaine: Optional[str] = None
    encadreur_id: Optional[int] = None


# ─────────────────────────────────────────────
# SCHÉMAS DE SORTIE (ce que l'API renvoie)
# ─────────────────────────────────────────────

class VersionMemoireReponse(BaseModel):
    """Représentation d'une version dans les réponses API."""
    id: int
    numero_version: int
    nom_fichier_original: str
    taille_fichier_ko: Optional[int]
    message_depot: Optional[str]
    est_version_courante: bool
    depose_le: datetime

    class Config:
        from_attributes = True  # Permet la conversion depuis un objet SQLAlchemy


class MemoireReponse(BaseModel):
    """Réponse complète pour un mémoire (avec ses versions)."""
    id: int
    titre: str
    description: Optional[str]
    domaine: Optional[str]
    annee_academique: Optional[str]
    statut: StatutMemoire
    etudiant_id: int
    encadreur_id: Optional[int]
    cree_le: datetime
    mis_a_jour_le: Optional[datetime]
    versions: List[VersionMemoireReponse] = []

    class Config:
        from_attributes = True


class MemoireResume(BaseModel):
    """Version courte pour les listes (sans les versions détaillées)."""
    id: int
    titre: str
    statut: StatutMemoire
    domaine: Optional[str]
    cree_le: datetime
    nb_versions: int = 0

    class Config:
        from_attributes = True
