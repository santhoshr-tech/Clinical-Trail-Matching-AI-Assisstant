from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from app.modules.chatbot import rag_service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatQueryRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "user-default"
    role: Optional[str] = "researcher"

@router.post("/query")
def process_chat_query(
    request: ChatQueryRequest,
    x_user_email: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None)
):
    try:
        user_id = x_user_email or request.user_id or "user-default"
        role = x_user_role or request.role or "researcher"
        
        result = rag_service.process_chatbot_query(
            user_id=user_id,
            role=role,
            message_text=request.message,
            conversation_id=request.conversation_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{conversation_id}")
def get_chat_history(conversation_id: str):
    try:
        history = rag_service.get_conversation_history(conversation_id)
        return {"success": True, "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
