from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import Token, LoginRequest, PasswordChangeRequest, OTPRequest, ResetPasswordRequest
import app.services.user_service as service
from app.core.security import create_access_token
from app.api.deps import get_current_active_user
from app.models.user import User

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
