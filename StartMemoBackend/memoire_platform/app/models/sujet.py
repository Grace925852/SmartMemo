import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class StatutSujet(str, enum.Enum):
    propose = "propose"
    en_evaluation = "en_evaluation"
    valide = "valide"
    rejete = "rejete"

class Sujet(Base):
    __tablename__ = "sujets"

    id = Column(Integer, primary_key=True)
    etudiant_id = Column(Integer, ForeignKey("etudiants.id"))
    titre = Column(String(500), nullable=False)
    description = Column(Text)
    domaine = Column(String(100))
    statut = Column(Enum(StatutSujet), default=StatutSujet.propose)
    score_faisabilite = Column(Float, nullable=True)
    score_similarite = Column(Float, nullable=True)
    commentaire_validation = Column(Text, nullable=True)
    valide_par = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    etudiant = relationship("Etudiant")
