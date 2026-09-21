import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, status

from app.models.auth import RegisterRequest, LoginRequest, UserOut, LoginResponse
from app.services.auth_service import auth_service, get_current_user

logger = logging.getLogger("auth_router")
router = APIRouter(prefix="", tags=["Authentication"])


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@router.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(request: Request, body: RegisterRequest):
    """
    Registers a new healthcare patient or user account.
    Checks uniqueness of email, securely hashes password with bcrypt,
    and returns created user details (without password hash).
    """
    logger.info("Registration attempt for email: %s", body.email)
    user = auth_service.register_user(body)
    return user


@router.post("/auth/login", response_model=LoginResponse)
@router.post("/api/auth/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest):
    """
    Authenticates user credentials.
    Enforces Redis rate limiting (max 5 failed attempts in 5 minutes).
    Returns JWT bearer token and user profile.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    logger.info("Login attempt for email: %s from IP: %s", body.email, client_ip)
    auth_result = auth_service.authenticate_user(body, client_ip=client_ip)
    return auth_result


@router.get("/auth/me", response_model=UserOut)
@router.get("/api/auth/me", response_model=UserOut)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the authenticated user's profile based on the verified JWT Bearer token.
    """
    return current_user


@router.post("/auth/logout")
@router.post("/api/auth/logout")
async def logout():
    """
    Logout endpoint. Informs client to discard stored credentials and tokens.
    """
    return {"message": "Successfully logged out. Client token cleared."}
