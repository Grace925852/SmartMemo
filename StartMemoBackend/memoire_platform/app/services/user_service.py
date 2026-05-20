from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, PasswordChangeRequest, ResetPasswordRequest
from app.core.security import get_password_hash, verify_password, generate_otp
from app.core.email import send_otp_email
from fastapi import HTTPException, status, BackgroundTasks
from datetime import datetime, timedelta

def create_user(db: Session, user_in: UserCreate):
    if len(user_in.password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères.")
    
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
    
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        nom=user_in.nom,
        prenom=user_in.prenom,
        role=user_in.role,
        telephone=user_in.telephone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, login_data: LoginRequest):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        return None
    if not verify_password(login_data.password, user.hashed_password):
        return None
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Ce compte a été désactivé. Contactez un administrateur.")
    return user

def change_password(db: Session, user_id: int, pwd_data: PasswordChangeRequest):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
    
    if not verify_password(pwd_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="L'ancien mot de passe est incorrect.")
    
    user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()
    return True

def create_otp_for_user(db: Session, email: str, background_tasks: BackgroundTasks):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Ne pas révéler si l'email existe ou non pour des raisons de sécurité
        return True 

    otp = generate_otp()
    user.otp_code = get_password_hash(otp) # On hash l'OTP en base comme un mot de passe
    user.otp_expire_at = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    background_tasks.add_task(send_otp_email, email, otp)
    return True

def reset_password_with_otp(db: Session, reset_data: ResetPasswordRequest):
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Requête invalide.")
    
    if not user.otp_code or not user.otp_expire_at:
        raise HTTPException(status_code=400, detail="Aucun code OTP n'a été demandé.")
        
    if datetime.utcnow() > user.otp_expire_at:
        raise HTTPException(status_code=400, detail="Le code OTP a expiré.")
        
    if not verify_password(reset_data.otp_code, user.otp_code):
        raise HTTPException(status_code=400, detail="Code OTP incorrect.")
        
    # Reset password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.otp_code = None
    user.otp_expire_at = None
    db.commit()
    return True
