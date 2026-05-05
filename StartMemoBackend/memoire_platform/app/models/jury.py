from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class MembreJury(Base):
    __tablename__ = "membres_jury"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    specialites = Column(Text)
    grade = Column(String(50))
    disponible = Column(Boolean, default=True)

    user = relationship("User")
