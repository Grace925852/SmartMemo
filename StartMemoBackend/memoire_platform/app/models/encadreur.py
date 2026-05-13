import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Encadreur(Base):
    __tablename__ = "encadreurs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    specialites = Column(Text)
    grade = Column(String(50))
    charge_actuelle = Column(String(10), default=0)
    max_etudiants = Column(String(10), default=5)
    disponible = Column(Boolean, default=True)

    user = relationship("User")
