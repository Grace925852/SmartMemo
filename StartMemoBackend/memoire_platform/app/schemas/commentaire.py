from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CommentaireCreate(BaseModel):
    version_id: int
    auteur_id: int
    contenu: str
    section: Optional[str] = None


class CommentaireOut(BaseModel):
    id: int
    version_id: int
    auteur_id: int
    contenu: str
    section: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
