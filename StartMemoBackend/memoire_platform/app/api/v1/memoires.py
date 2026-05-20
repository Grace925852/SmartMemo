from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

import enum
from app.models.memoire import StatutMemoire

class StatutVersion(str, enum.Enum):
    en_attente    = "en_attente"
    en_correction = "en_correction"
    valide        = "valide"
    refuse        = "refuse"


class MemoireCreate(BaseModel):
    etudiant_id: int
    sujet_id: int
    encadreur_id: Optional[int] = None
    titre_final: Optional[str] = None


class MemoireUpdateStatut(BaseModel):
    statut: StatutMemoire


class MemoireOut(BaseModel):
    id: int
    etudiant_id: int
    sujet_id: int
    encadreur_id: Optional[int] = None
    titre_final: Optional[str] = None
    statut: StatutMemoire
    score_plagiat: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionMemoireCreate(BaseModel):
    memoire_id: int
    numero_version: int
    chemin_fichier: str
    nom_fichier: str
    taille_fichier: int


class VersionMemoireUpdateStatut(BaseModel):
    statut: StatutVersion


class VersionMemoireOut(BaseModel):
    id: int
    memoire_id: int
    numero_version: int
    chemin_fichier: Optional[str] = None
    nom_fichier: Optional[str] = None
    taille_fichier: Optional[int] = None
    statut: StatutVersion
    depose_le: datetime

    model_config = ConfigDict(from_attributes=True)
