from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class VersionMemoire(Base):
    """
    Chaque dépôt d'un fichier crée une nouvelle ligne ici.

    Exemple :
      - Version 1 : fichier_v1.pdf, déposé le 01/06/2025
      - Version 2 : fichier_v2.pdf, déposé le 15/06/2025 (après corrections)
      - Version 3 : fichier_v3.pdf, déposé le 28/06/2025 (version finale)
    """
    __tablename__ = "versions_memoire"

    # --- Identifiant ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # --- Lien vers le mémoire parent ---
    memoire_id = Column(UUID(as_uuid=True), ForeignKey("memoires.id"), nullable=False)

    # --- Numéro de version (1, 2, 3 ...) ---
    numero_version = Column(Integer, nullable=False, default=1)

    # --- Fichier déposé ---
    nom_fichier_original = Column(String(255), nullable=False)
    nom_fichier_stocke   = Column(String(255), nullable=False)
    chemin_fichier       = Column(String(500), nullable=False)
    taille_fichier_ko    = Column(Integer, nullable=True)

    # --- Message accompagnant le dépôt ---
    message_depot = Column(Text, nullable=True)

    # --- Indique si c'est la version actuellement active ---
    est_version_courante = Column(Boolean, default=True, nullable=False)

    # --- Qui a déposé ---
    depose_par_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # --- Timestamp ---
    depose_le = Column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relations ORM ---
    memoire    = relationship("Memoire", back_populates="versions")
    depose_par = relationship("User")

    def __repr__(self):
        return (
            f"<VersionMemoire "
            f"memoire_id={self.memoire_id} "
            f"v{self.numero_version} "
            f"fichier='{self.nom_fichier_stocke}'>"
        )
