from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Affectation(Base):
    __tablename__ = "affectations"

    id = Column(Integer, primary_key=True)
    etudiant_id = Column(Integer, ForeignKey("etudiants.id"), unique=True)
    encadreur_id = Column(Integer, ForeignKey("encadreurs.id"))
    memoire_id = Column(Integer, ForeignKey("memoires.id"))
    date_affectation = Column(DateTime, default=func.now())
    actif = Column(Boolean, default=True)

    etudiant = relationship("Etudiant")
    encadreur = relationship("Encadreur")
    memoire = relationship("Memoire")
