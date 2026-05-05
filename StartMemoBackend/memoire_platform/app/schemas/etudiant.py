from pydantic import BaseModel, ConfigDict
from typing import Optional

class EtudiantBase(BaseModel):
    numero_etudiant: str
    filiere: str
    niveau: str
    annee_inscription: int

class EtudiantCreate(EtudiantBase):
    user_id: int

class EtudiantOut(EtudiantBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
