# app/schemas/version_schema.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NouveauDepot(BaseModel):
    """
    Message optionnel accompagnant un nouveau dépôt de fichier.
    Le fichier lui-même est envoyé via multipart/form-data.
    """
    message_depot: Optional[str] = Field(
        None,
        example="Corrections effectuées suite aux remarques du chapitre 2"
    )


class VersionReponse(BaseModel):
    id: int
    memoire_id: int
    numero_version: int
    nom_fichier_original: str
    nom_fichier_stocke: str
    taille_fichier_ko: Optional[int]
    message_depot: Optional[str]
    est_version_courante: bool
    depose_le: datetime

    class Config:
        from_attributes = True
