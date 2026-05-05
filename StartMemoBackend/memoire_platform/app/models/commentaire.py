from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Commentaire(Base):
    __tablename__ = "commentaires"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("versions_memoire.id"))
    auteur_id = Column(Integer, ForeignKey("users.id"))
    contenu = Column(Text, nullable=False)
    section = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())

    version = relationship("VersionMemoire")
    auteur = relationship("User")
