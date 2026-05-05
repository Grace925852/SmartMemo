from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Encadreur(Base):
    __tablename__ = "encadreurs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    specialites = Column(Text)
    grade = Column(String(50))
    charge_actuelle = Column(Integer, default=0)
    max_etudiants = Column(Integer, default=5)
    disponible = Column(Boolean, default=True)

    user = relationship("User")
