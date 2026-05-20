"""
Script pour supprimer et recréer toutes les tables avec les nouvelles colonnes UUID.
À exécuter UNE SEULE FOIS pour réinitialiser le schéma.
"""
from app.database import engine, Base
import app.models  # Charge tous les modèles

print("Suppression de toutes les tables...")
Base.metadata.drop_all(bind=engine)
print("Tables supprimées.")

print("Recréation de toutes les tables avec le nouveau schéma UUID...")
Base.metadata.create_all(bind=engine)
print("Tables recréées avec succès !")
print("\nVous pouvez maintenant marquer la migration Alembic comme appliquée.")
