from fastapi import FastAPI
from app.database import Base, engine
import app.models

app = FastAPI(title="Plateforme Mémoire IPNET", version="1.0.0")

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Plateforme Mémoire IPNET", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
