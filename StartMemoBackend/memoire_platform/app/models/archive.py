import uuid
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Archive(Base):
    __tablename__ = "archives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    memoire_id = Column(UUID(as_uuid=True), ForeignKey("memoires.id"), unique=True)
    titre = Column(String(500))
    auteur_nom = Column(String(200))
    annee_soutenance = Column(Integer)
    filiere = Column(String(100))
    domaine = Column(String(100))
    mots_cles = Column(Text)
    resume = Column(Text)
    chemin_fichier = Column(String(500))
    acces_public = Column(Boolean, default=False)
    archive_le = Column(DateTime, default=func.now())

    memoire = relationship("Memoire")
