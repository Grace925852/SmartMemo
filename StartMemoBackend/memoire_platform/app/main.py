from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine
import app.models
from app.api.v1 import routes_memoire, routes_sujet, routes_soutenance, routes_auth, routes_encadreur
from app.services.ia import antiplagiat_service, approval_service, submission_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ex cut  au d marrage et   l'arr t de l'application."""
    print("[START] SmartMemo d marre   chargement des mod les IA...")
    
    # Cr ation des tables DB
    Base.metadata.create_all(bind=engine)
    
    # Pr -chargement des mod les IA (si existants)
    try:
        antiplagiat_service.charger_modele()
        print("  [OK] Mod le AntiPlagiat charg ")
    except Exception as e:
        print(f"  [WARN] AntiPlagiat non charg : {e}")
    
    try:
        approval_service.charger_modele()
        print("  [OK] Mod le Approval charg ")
    except Exception as e:
        print(f"  [WARN] Approval non charg : {e}")
        
    try:
        submission_service.charger_modele()
        print("  [OK] Mod le Submission charg ")
    except Exception as e:
        print(f"  [WARN] Submission non charg : {e}")
    
    print("[OK] Initialisation termin e.")
    yield
    print("  Arr t de SmartMemo.")

app = FastAPI(
    title="SmartMemo API",
    description="Plateforme intelligente de gestion des m moires acad miques",
    version="1.0.0",
    lifespan=lifespan
)

# Enregistrer les routes
app.include_router(routes_auth.router, prefix="/api/v1")
app.include_router(routes_memoire.router, prefix="/api/v1")
app.include_router(routes_sujet.router, prefix="/api/v1")
app.include_router(routes_soutenance.router, prefix="/api/v1")
app.include_router(routes_encadreur.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Plateforme M moire IPNET - API SmartMemo", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
