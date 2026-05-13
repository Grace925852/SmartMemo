import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Etudiant(Base):
    __tablename__ = "etudiants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    numero_etudiant = Column(String(50), unique=True)
    filiere = Column(String(100))
    niveau = Column(String(20))
    annee_inscription = Column(String(9))
    competences = Column(Text)
    centres_interet = Column(Text)

    user = relationship("User")
    memoires = relationship("Memoire", back_populates="etudiant")
