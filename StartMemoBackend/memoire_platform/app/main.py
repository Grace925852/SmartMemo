from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models

from app.api.v1.memoires import router as memoires_router
from app.api.v1.commentaires import router as commentaires_router
from app.api.v1.integration import router as integration_router


app = FastAPI(
    title="Plateforme Mémoire IPNET",
    version="1.0.0"
)

# Autorise le frontend à communiquer avec le backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer * par l'URL exacte du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {
        "message": "Plateforme Mémoire IPNET",
        "status": "ok"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# Routes 
app.include_router(memoires_router)
app.include_router(commentaires_router)
app.include_router(integration_router)