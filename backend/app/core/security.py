from fastapi import Depends, HTTPException, Header, status
from typing import List, Optional, Dict, Any
from app.schemas.common import UserRole
from app.core.db import get_db_connection

class AuthenticatedUser:
    def __init__(self, user_id: str, email: str, role: UserRole, full_name: str):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.full_name = full_name

def get_current_user(
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(default="coordinator@clinicaltrial.ai", alias="X-User-Email")
) -> AuthenticatedUser:
    """Extract authenticated user session from header or active token context."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, full_name FROM profiles WHERE email = ?;", (x_user_email,))
    row = cursor.fetchone()
    conn.close()

    # Determine active role (Header override takes precedence for active session switching)
    if x_user_role and x_user_role in [r.value for r in UserRole]:
        active_role = UserRole(x_user_role)
    elif row:
        active_role = UserRole(row["role"])
    else:
        active_role = UserRole.RESEARCH_COORDINATOR

    user_id = row["id"] if row else "00000000-0000-0000-0000-000000000002"
    full_name = row["full_name"] if row else f"User ({active_role.value})"

    return AuthenticatedUser(
        user_id=user_id,
        email=x_user_email or "coordinator@clinicaltrial.ai",
        role=active_role,
        full_name=full_name
    )

def require_role(allowed_roles: List[UserRole]):
    """FastAPI Dependency for Role-Based Access Control (RBAC)."""
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not authorized to access this resource. Allowed: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker
