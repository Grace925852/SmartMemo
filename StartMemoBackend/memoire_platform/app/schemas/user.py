from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import RoleEnum

class UserBase(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    role: RoleEnum
    telephone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
