from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import Token, LoginRequest, PasswordChangeRequest, OTPRequest, ResetPasswordRequest
import app.services.user_service as service
from app.core.security import create_access_token
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.etudiant import Etudiant
from app.models.encadreur import Encadreur
from app.models.jury import MembreJury

router = APIRouter(
    prefix="/auth",
    tags=["Authentification"]
)

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Inscription d'un nouvel utilisateur (Route publique)."""
    return service.create_user(db, user_in)

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Connexion pour récupérer un token JWT (Route publique)."""
    user = service.authenticate_user(db, login_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"id": str(user.id), "role": user.role.value, "sub": user.email}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "id": user.id
    }

@router.post("/change-password")
def change_password(
    pwd_data: PasswordChangeRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Change le mot de passe de l'utilisateur connecté (Route protégée)."""
    service.change_password(db, current_user.id, pwd_data)
    return {"message": "Mot de passe mis à jour avec succès"}

@router.post("/forgot-password")
def forgot_password(
    otp_req: OTPRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Demande un code OTP envoyé par email (Route publique)."""
    service.create_otp_for_user(db, otp_req.email, background_tasks)
    return {"message": "Si l'adresse email existe, un code OTP vous sera envoyé."}

@router.post("/reset-password")
def reset_password(reset_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe à l'aide de l'OTP (Route publique)."""
    service.reset_password_with_otp(db, reset_data)
    return {"message": "Mot de passe réinitialisé avec succès"}


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Retourne le profil enrichi de l'utilisateur connecté selon son rôle."""
    role = current_user.role.value

    base: Dict[str, Any] = {
        "id": str(current_user.id),
        "nom": current_user.nom,
        "prenom": current_user.prenom,
        "email": current_user.email,
        "role": role,
    }

    if role == "etudiant":
        etudiant = (
            db.query(Etudiant)
            .filter(Etudiant.user_id == current_user.id)
            .first()
        )
        competences: List[str] = []
        if etudiant and etudiant.competences:
            competences = [c.strip() for c in etudiant.competences.split(",") if c.strip()]
        base["profil"] = {
            "filiere": etudiant.filiere if etudiant else None,
            "niveau": etudiant.niveau if etudiant else None,
            "annee_inscription": etudiant.annee_inscription if etudiant else None,
            "competences": competences
        }

    elif role == "encadreur":
        encadreur = (
            db.query(Encadreur)
            .filter(Encadreur.user_id == current_user.id)
            .first()
        )
        specialites: List[str] = []
        if encadreur and encadreur.specialites:
            specialites = [s.strip() for s in encadreur.specialites.split(",") if s.strip()]
        try:
            charge = int(encadreur.charge_actuelle) if encadreur and encadreur.charge_actuelle else 0
        except (ValueError, TypeError):
            charge = 0
        try:
            max_et = int(encadreur.max_etudiants) if encadreur and encadreur.max_etudiants else 5
        except (ValueError, TypeError):
            max_et = 5
        base["profil"] = {
            "specialites": specialites,
            "grade": encadreur.grade if encadreur else None,
            "charge_actuelle": charge,
            "max_etudiants": max_et
        }

    elif role == "jury":
        membre = (
            db.query(MembreJury)
            .filter(MembreJury.user_id == current_user.id)
            .first()
        )
        specialites_jury: List[str] = []
        if membre and membre.specialites:
            specialites_jury = [s.strip() for s in membre.specialites.split(",") if s.strip()]
        base["profil"] = {
            "specialites": specialites_jury,
            "grade": membre.grade if membre else None
        }

    else:
        base["profil"] = {}

    return base
