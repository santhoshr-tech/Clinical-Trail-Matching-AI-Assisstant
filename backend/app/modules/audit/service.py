import uuid
import json
import logging
from typing import Optional, Dict, Any
from app.core.db import get_db_connection

logger = logging.getLogger("clinical_trial_assistant")

def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = "127.0.0.1",
    user_agent: Optional[str] = "FastAPI Backend"
) -> str:
    """
    Log an immutable audit trail entry.
    Actions supported:
    - AUTHENTICATION (Login, Logout, Token Refresh)
    - DATA_CHANGE (Patient Insert/Update, Record Edit)
    - EXTRACTION_APPROVAL (Fact Verification/Approval)
    - SCREENING_RUN (Matching Execution)
    - REVIEW_SUBMIT (Investigator/CRC Review Sign-off)
    - VERIFICATION (Evidence Verification)
    - EXPORT (Report/Dataset Export)
    - CONFIG_CHANGE (Provider/System Setting Change)
    """
    audit_id = str(uuid.uuid4())
    payload_str = json.dumps(payload) if payload else "{}"
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, payload_json, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (audit_id, user_id, action, entity_type, entity_id, payload_str, ip_address, user_agent))
        conn.commit()
        conn.close()
        logger.info(f"[AUDIT] {action} on {entity_type}:{entity_id} by user:{user_id} registered successfully.")
    except Exception as e:
        logger.error(f"[AUDIT ERROR] Failed to record audit log: {e}")

    return audit_id

def get_recent_audit_logs(limit: int = 50) -> list:
    """Retrieve audit log records for governance view."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, action, entity_type, entity_id, payload_json, ip_address, timestamp
        FROM audit_logs
        ORDER BY timestamp DESC
        LIMIT ?;
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            "id": r["id"],
            "userId": r["user_id"],
            "action": r["action"],
            "entityType": r["entity_type"],
            "entityId": r["entity_id"],
            "payload": json.loads(r["payload_json"]) if r["payload_json"] else {},
            "ipAddress": r["ip_address"],
            "timestamp": r["timestamp"]
        })
    return logs
