from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.sujet import StatutSujet

class SujetBase(BaseModel):
    titre: str
    description: Optional[str] = None
    domaine: Optional[str] = None

class SujetCreate(SujetBase):
    etudiant_id: int

class SujetOut(SujetBase):
    id: int
    statut: StatutSujet
    score_faisabilite: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
