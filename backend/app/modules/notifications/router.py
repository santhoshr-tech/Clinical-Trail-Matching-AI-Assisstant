from fastapi import APIRouter
from app.schemas.common import ApiResponse
from app.core.db import get_db_connection, init_db

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=ApiResponse[list])
async def list_notifications():
    """Retrieve all in-app notifications (missed-week alerts, re-screening state changes, system updates)."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, message, is_read as isRead, created_at FROM coordinator_notifications ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        notifs = [dict(r) for r in rows]

        if not notifs:
            notifs = [{"id": "notif-1", "title": "System Active", "message": "Clinical Trial Matching Platform Operating Normally", "isRead": False}]

        return ApiResponse(data=notifs)
