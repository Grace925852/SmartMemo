import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class StatutMemoire(str, enum.Enum):
    en_cours = "en_cours"
    en_attente = "en_attente"
    en_correction = "en_correction"
    valide = "valide"
    refuse = "refuse"
    soutenu = "soutenu"

class StatutVersion(str, enum.Enum):
    en_attente = "en_attente"
    en_correction = "en_correction"
    valide = "valide"
    refuse = "refuse"

class Memoire(Base):
    __tablename__ = "memoires"

    id = Column(Integer, primary_key=True)
    etudiant_id = Column(Integer, ForeignKey("etudiants.id"), unique=True)
    sujet_id = Column(Integer, ForeignKey("sujets.id"))
    encadreur_id = Column(Integer, ForeignKey("encadreurs.id"), nullable=True)
    titre_final = Column(String(500), nullable=True)
    statut = Column(Enum(StatutMemoire), default=StatutMemoire.en_cours)
    score_plagiat = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class VersionMemoire(Base):
    __tablename__ = "versions_memoire"

    id = Column(Integer, primary_key=True)
    memoire_id = Column(Integer, ForeignKey("memoires.id"))
    numero_version = Column(Integer, nullable=False)
    chemin_fichier = Column(String(500))
    nom_fichier = Column(String(255))
    taille_fichier = Column(Integer)
    statut = Column(Enum(StatutVersion), default=StatutVersion.en_attente)
    depose_le = Column(DateTime, default=func.now())

    memoire = relationship("Memoire")
