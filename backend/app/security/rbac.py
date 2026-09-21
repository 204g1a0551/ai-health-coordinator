"""
Role-Based Access Control (RBAC) definitions, permission mapping,
and FastAPI authorization dependencies.
"""

from enum import Enum
from typing import List, Set, Dict, Any, Optional
from fastapi import HTTPException, status, Header, Depends
import jwt
from app.config import auth_settings


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class Permission(str, Enum):
    READ_OWN_DOCUMENTS = "read:own_documents"
    WRITE_OWN_DOCUMENTS = "write:own_documents"
    READ_PATIENT_DOCUMENTS = "read:patient_documents"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"
    REVOKE_CONSENT = "revoke:consent"
    EXECUTE_ERASURE = "execute:erasure"
    VIEW_SECURITY_STATUS = "view:security_status"
    WRITE_PRESCRIPTION = "write:prescription"


ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.PATIENT: {
        Permission.READ_OWN_DOCUMENTS,
        Permission.WRITE_OWN_DOCUMENTS,
        Permission.REVOKE_CONSENT,
        Permission.EXECUTE_ERASURE,
    },
    UserRole.DOCTOR: {
        Permission.READ_PATIENT_DOCUMENTS,
        Permission.WRITE_PRESCRIPTION,
        Permission.READ_OWN_DOCUMENTS,
    },
    UserRole.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_SECURITY_STATUS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.READ_OWN_DOCUMENTS,
    },
    UserRole.AUDITOR: {
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_SECURITY_STATUS,
    }
}


def has_permission(role_str: str, permission: Permission) -> bool:
    """Checks if a given role has the requested permission."""
    try:
        role = UserRole(role_str.upper())
        return permission in ROLE_PERMISSIONS.get(role, set())
    except (ValueError, KeyError):
        return False


def get_current_user_context(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Decodes the JWT token from the Authorization header and returns user context.
    Falls back to a demo PATIENT user if no valid token is provided (for dev/demo compatibility),
    while preserving strict role restrictions when explicit role headers or tokens exist.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            payload = jwt.decode(
                token, 
                auth_settings.jwt_secret, 
                algorithms=[auth_settings.jwt_algorithm]
            )
            role_str = payload.get("role", UserRole.PATIENT.value).upper()
            return {
                "id": payload.get("sub") or payload.get("user_id") or "user_default",
                "email": payload.get("email", ""),
                "role": role_str,
                "is_authenticated": True
            }
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials."
            )

    # Default fallback for unauthenticated endpoints or local session mock
    return {
        "id": "usr_default_patient",
        "email": "patient@example.com",
        "role": UserRole.PATIENT.value,
        "is_authenticated": False
    }


def require_role(allowed_roles: List[UserRole]):
    """FastAPI dependency to enforce one of the allowed roles."""
    def dependency(user: Dict[str, Any] = Depends(get_current_user_context)) -> Dict[str, Any]:
        user_role_str = user.get("role", "").upper()
        allowed_str_roles = [r.value for r in allowed_roles]
        if user_role_str not in allowed_str_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {allowed_str_roles}. Current role: {user_role_str}"
            )
        return user
    return dependency


def require_permission(permission: Permission):
    """FastAPI dependency to enforce a specific permission."""
    def dependency(user: Dict[str, Any] = Depends(get_current_user_context)) -> Dict[str, Any]:
        user_role_str = user.get("role", "")
        if not has_permission(user_role_str, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permission: {permission.value}"
            )
        return user
    return dependency
