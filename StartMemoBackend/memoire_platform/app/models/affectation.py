import uuid
from sqlalchemy import Column, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Affectation(Base):
    __tablename__ = "affectations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    etudiant_id = Column(UUID(as_uuid=True), ForeignKey("etudiants.id"), unique=True)
    encadreur_id = Column(UUID(as_uuid=True), ForeignKey("encadreurs.id"))
    memoire_id = Column(UUID(as_uuid=True), ForeignKey("memoires.id"))
    date_affectation = Column(DateTime, default=func.now())
    actif = Column(Boolean, default=True)

    etudiant = relationship("Etudiant")
    encadreur = relationship("Encadreur")
    memoire = relationship("Memoire")
