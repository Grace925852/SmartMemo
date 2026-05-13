import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class MembreJury(Base):
    __tablename__ = "membres_jury"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    specialites = Column(Text)
    grade = Column(String(50))
    disponible = Column(Boolean, default=True)

    user = relationship("User")
