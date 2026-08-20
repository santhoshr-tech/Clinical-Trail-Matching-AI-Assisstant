from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.schemas.common import ApiResponse, UserRole
from app.core.security import get_current_user, AuthenticatedUser
from app.modules.audit.service import log_audit_event
from app.core.db import get_db_connection

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    role: UserRole

@router.post("/login", response_model=ApiResponse[dict])
async def login(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, full_name, role FROM profiles WHERE email = ?;", (request.email,))
    user = cursor.fetchone()
    conn.close()

    user_id = user["id"] if user else "00000000-0000-0000-0000-000000000002"
    full_name = user["full_name"] if user else f"User ({request.role.value})"

    log_audit_event(
        action="AUTHENTICATION",
        entity_type="user_session",
        entity_id=user_id,
        user_id=user_id,
        payload={"event": "LOGIN_SUCCESS", "email": request.email, "role": request.role.value}
    )

    return ApiResponse(data={
        "token": f"prototype-jwt-token-{user_id}",
        "user": {
            "id": user_id,
            "email": request.email,
            "fullName": full_name,
            "role": request.role.value
        }
    })

@router.post("/logout", response_model=ApiResponse[dict])
async def logout(current_user: AuthenticatedUser = Depends(get_current_user)):
    log_audit_event(
        action="AUTHENTICATION",
        entity_type="user_session",
        entity_id=current_user.user_id,
        user_id=current_user.user_id,
        payload={"event": "LOGOUT_SUCCESS", "email": current_user.email}
    )

    return ApiResponse(data={"message": "Successfully logged out session."})

@router.get("/me", response_model=ApiResponse[dict])
async def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return ApiResponse(data={
        "id": current_user.user_id,
        "email": current_user.email,
        "fullName": current_user.full_name,
        "role": current_user.role.value
    })
