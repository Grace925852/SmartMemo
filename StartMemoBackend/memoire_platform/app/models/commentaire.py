import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Commentaire(Base):
    __tablename__ = "commentaires"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("versions_memoire.id"))
    auteur_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    contenu = Column(Text, nullable=False)
    section = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())

    version = relationship("VersionMemoire")
    auteur = relationship("User")
