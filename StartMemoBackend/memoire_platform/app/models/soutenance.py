import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class StatutSoutenance(str, enum.Enum):
    planifiee = "planifiee"
    confirmee = "confirmee"
    reportee = "reportee"
    terminee = "terminee"

class Soutenance(Base):
    __tablename__ = "soutenances"

    id = Column(Integer, primary_key=True)
    memoire_id = Column(Integer, ForeignKey("memoires.id"), unique=True)
    date_soutenance = Column(DateTime, nullable=True)
    salle = Column(String(100), nullable=True)
    statut = Column(Enum(StatutSoutenance), default=StatutSoutenance.planifiee)
    president_jury_id = Column(Integer, ForeignKey("membres_jury.id"), nullable=True)
    examinateur_id = Column(Integer, ForeignKey("membres_jury.id"), nullable=True)
    note_finale = Column(Float, nullable=True)
    mention = Column(String(50), nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    memoire = relationship("Memoire")
    president_jury = relationship("MembreJury", foreign_keys=[president_jury_id])
    examinateur = relationship("MembreJury", foreign_keys=[examinateur_id])
