from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class StatutMemoire(str, enum.Enum):
    """
    Les 4 statuts possibles d'un mémoire (en minuscules pour la BDD).
    """
    en_attente    = "en_attente"
    en_correction = "en_correction"
    valide        = "valide"
    refuse        = "refuse"


class Memoire(Base):
    __tablename__ = "memoires"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    titre = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    domaine = Column(String(100), nullable=True)
    annee_academique = Column(String(10), nullable=True)

    statut = Column(
        Enum(StatutMemoire),
        default=StatutMemoire.en_attente,
        nullable=False
    )

    etudiant_id = Column(UUID(as_uuid=True), ForeignKey("etudiants.id"), nullable=False)
    encadreur_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    cree_le = Column(DateTime(timezone=True), default=datetime.utcnow)
    mis_a_jour_le = Column(DateTime(timezone=True), onupdate=func.now())

    etudiant = relationship("Etudiant", back_populates="memoires")
    versions = relationship(
        "VersionMemoire",
        back_populates="memoire",
        order_by="VersionMemoire.numero_version.desc()"
    )

    def __repr__(self):
        return f"<Memoire id={self.id} titre='{self.titre}' statut={self.statut}>"
