from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models
from app.api.v1 import (
    routes_memoire,
    routes_sujet,
    routes_soutenance,
    routes_auth,
    routes_encadreur,
    routes_admin,
    routes_jury,
    routes_archive,
    routes_etudiant,
)
from app.api.v1.commentaires import router as commentaires_router
from app.api.v1.integration import router as integration_router
from app.services.ia import antiplagiat_service, approval_service, submission_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Execute au demarrage et a l'arret de l'application."""
    print("[START] SmartMemo demarre — chargement des modeles IA...")

    Base.metadata.create_all(bind=engine)

    try:
        antiplagiat_service.charger_modele()
        print("  [OK] Modele AntiPlagiat charge")
    except Exception as e:
        print(f"  [WARN] AntiPlagiat non charge : {e}")

    try:
        approval_service.charger_modele()
        print("  [OK] Modele Approval charge")
    except Exception as e:
        print(f"  [WARN] Approval non charge : {e}")

    try:
        submission_service.charger_modele()
        print("  [OK] Modele Submission charge")
    except Exception as e:
        print(f"  [WARN] Submission non charge : {e}")

    print("[OK] Initialisation terminee.")
    yield
    print("  Arret de SmartMemo.")


app = FastAPI(
    title="SmartMemo API",
    description="Plateforme intelligente de gestion des memoires academiques",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(routes_auth.router, prefix="/api/v1")

# Memoires + IA
app.include_router(routes_memoire.router, prefix="/api/v1")
app.include_router(routes_sujet.router, prefix="/api/v1")
app.include_router(routes_soutenance.router, prefix="/api/v1")

# Encadreur (lex-dev)
app.include_router(routes_encadreur.router, prefix="/api/v1")

# Etudiant (paul-dev)
app.include_router(routes_etudiant.router, prefix="/api/v1")

# Admin, Jury, Archive (lry-dev)
app.include_router(routes_admin.router, prefix="/api/v1")
app.include_router(routes_jury.router, prefix="/api/v1")
app.include_router(routes_archive.router, prefix="/api/v1")

# Commentaires + Integration (atta_esso)
app.include_router(commentaires_router)
app.include_router(integration_router)


@app.get("/")
def read_root():
    return {"message": "Plateforme Memoire IPNET - API SmartMemo", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
