from typing import Optional
import re
from pydantic import BaseModel, Field, field_validator


EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full legal or preferred name")
    email: str = Field(..., description="Valid personal or work email address")
    phone: str = Field(..., min_length=8, max_length=20, description="Contact phone number")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 chars)")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or readable format")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean):
            raise ValueError("Please provide a valid email address (e.g., patient@example.com).")
        return clean

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in v) and not any(c.islower() for c in v):
            raise ValueError("Password must contain letters.")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered account email")
    password: str = Field(..., description="Account password")
    remember_me: Optional[bool] = Field(default=False, description="Extend session duration")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean):
            raise ValueError("Please provide a valid email address.")
        return clean


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    dob: Optional[str] = None
    created_at: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class TokenPayload(BaseModel):
    sub: str
    email: str
    name: str
    exp: int
    iat: int
