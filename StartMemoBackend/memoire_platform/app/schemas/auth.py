from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    id: UUID

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    id: Optional[str] = None  # stocké comme str dans JWT, converti ensuite

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class OTPRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str
