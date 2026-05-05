from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Etudiant(Base):
    __tablename__ = "etudiants"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    numero_etudiant = Column(String(50), unique=True)
    filiere = Column(String(100))
    niveau = Column(String(20))
    annee_inscription = Column(Integer)
    competences = Column(Text)
    centres_interet = Column(Text)

    user = relationship("User")
