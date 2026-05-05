from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.memoire import StatutMemoire, StatutVersion

class MemoireBase(BaseModel):
    etudiant_id: int
    sujet_id: int

class MemoireOut(MemoireBase):
    id: int
    statut: StatutMemoire
    score_plagiat: Optional[float] = None
    encadreur_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class VersionMemoireCreate(BaseModel):
    memoire_id: int
    numero_version: int
    chemin_fichier: str
    nom_fichier: str
    taille_fichier: int

class VersionMemoireOut(BaseModel):
    id: int
    statut: StatutVersion
    depose_le: datetime

    model_config = ConfigDict(from_attributes=True)
