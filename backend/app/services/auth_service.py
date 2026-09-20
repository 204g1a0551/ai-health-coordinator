import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import bcrypt
import jwt
from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import auth_settings
from app.db.repository import (
    create_user_record,
    get_user_by_email,
    get_user_by_id,
)
from app.models.auth import RegisterRequest, LoginRequest
from app.services.redis_service import redis_service

logger = logging.getLogger("auth_service")
security = HTTPBearer(auto_error=False)


class AuthService:
    """
    Handles authentication, password hashing, JWT lifecycle, and Redis rate limiting.
    Passwords are never stored in plain text or returned in API responses.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt with automatic salt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception as e:
            logger.error("Password verification error: %s", str(e))
            return False

    @staticmethod
    def create_access_token(user: Dict[str, Any], remember_me: bool = False) -> Tuple[str, int]:
        """
        Creates a signed JWT access token.
        If remember_me is True, duration is 7 days; otherwise standard configured duration (e.g. 24 hours).
        Returns (token_str, expires_in_seconds).
        """
        if remember_me:
            expires_delta = timedelta(days=7)
        else:
            expires_delta = timedelta(minutes=auth_settings.access_token_expire_minutes)

        now = datetime.utcnow()
        expire = now + expires_delta
        expires_in = int(expires_delta.total_seconds())

        payload = {
            "sub": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        token = jwt.encode(
            payload,
            auth_settings.jwt_secret,
            algorithm=auth_settings.jwt_algorithm
        )
        return token, expires_in

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Validates and decodes a signed JWT access token."""
        try:
            payload = jwt.decode(
                token,
                auth_settings.jwt_secret,
                algorithms=[auth_settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token received.")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token received: %s", str(e))
            return None

    def register_user(self, data: RegisterRequest) -> Dict[str, Any]:
        """Registers a new user after checking email uniqueness."""
        email_clean = data.email.strip().lower()
        existing = get_user_by_email(email_clean)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists."
            )

        hashed_password = self.hash_password(data.password)
        user_record = {
            "full_name": data.full_name.strip(),
            "email": email_clean,
            "phone": data.phone.strip(),
            "dob": data.dob.strip() if data.dob else None,
            "password_hash": hashed_password,
        }

        created = create_user_record(user_record)
        # Return sanitized user without password_hash
        return {
            "id": created["id"],
            "full_name": created["full_name"],
            "email": created["email"],
            "phone": created["phone"],
            "dob": created.get("dob"),
            "created_at": created.get("created_at"),
        }

    def authenticate_user(self, data: LoginRequest, client_ip: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Authenticates a user with email + password, enforcing Redis rate limiting.
        """
        email_clean = data.email.strip().lower()
        rate_key = f"{client_ip}:{email_clean}"

        # 1. Check rate limit
        allowed, remaining = redis_service.check_login_rate_limit(
            rate_key,
            max_attempts=auth_settings.login_rate_limit_attempts
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again in 5 minutes."
            )

        # 2. Look up user
        user = get_user_by_email(email_clean)
        if not user or not self.verify_password(data.password, user.get("password_hash", "")):
            # Record failed attempt
            failed_count = redis_service.record_failed_login(
                rate_key,
                window_seconds=auth_settings.login_rate_limit_window
            )
            attempts_left = max(0, auth_settings.login_rate_limit_attempts - failed_count)
            logger.warning(
                "Failed login attempt for %s from IP %s. Remaining: %s",
                email_clean, client_ip, attempts_left
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid email or password. {attempts_left} attempts remaining before temporary lockout."
            )

        # 3. Successful login - clear rate limit
        redis_service.clear_login_rate_limit(rate_key)

        # 4. Generate JWT
        token, expires_in = self.create_access_token(user, remember_me=bool(data.remember_me))

        sanitized_user = {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "dob": user.get("dob"),
            "created_at": user.get("created_at"),
        }

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": sanitized_user,
        }

    def get_current_user_from_token(self, token: str) -> Dict[str, Any]:
        """Validates token and returns current user profile."""
        payload = self.decode_access_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with this token no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "dob": user.get("dob"),
            "created_at": user.get("created_at"),
        }


auth_service = AuthService()


async def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """FastAPI dependency for protected routes."""
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.get_current_user_from_token(auth_credentials.credentials)
