from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine
import app.models
from app.api.v1 import routes_memoire, routes_sujet, routes_soutenance
from app.services.ia import antiplagiat_service, approval_service, submission_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Exécuté au démarrage et à l'arrêt de l'application."""
    print("🚀 SmartMemo démarre — chargement des modèles IA...")
    
    # Création des tables DB
    Base.metadata.create_all(bind=engine)
    
    # Pré-chargement des modèles IA (si existants)
    try:
        antiplagiat_service.charger_modele()
        print("  ✅ Modèle AntiPlagiat chargé")
    except Exception as e:
        print(f"  ⚠️ AntiPlagiat non chargé: {e}")
    
    try:
        approval_service.charger_modele()
        print("  ✅ Modèle Approval chargé")
    except Exception as e:
        print(f"  ⚠️ Approval non chargé: {e}")
        
    try:
        submission_service.charger_modele()
        print("  ✅ Modèle Submission chargé")
    except Exception as e:
        print(f"  ⚠️ Submission non chargé: {e}")
    
    print("✅ Initialisation terminée.")
    yield
    print("🛑 Arrêt de SmartMemo.")

app = FastAPI(
    title="SmartMemo API",
    description="Plateforme intelligente de gestion des mémoires académiques",
    version="1.0.0",
    lifespan=lifespan
)

# Enregistrer les routes
app.include_router(routes_memoire.router, prefix="/api/v1")
app.include_router(routes_sujet.router, prefix="/api/v1")
app.include_router(routes_soutenance.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Plateforme Mémoire IPNET - API SmartMemo", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
