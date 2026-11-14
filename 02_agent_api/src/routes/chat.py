from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers.chat_controller import get_history, get_sessions, handle_chat
import json
from fastapi.responses import StreamingResponse
from src.repositories import SessionLocal, get_db
from src.services.agent_service import AgentService
from src.dto.api_entities import ChatRequest, ChatResponse, HistoryItem, UserSessionsResponse

chat_router = APIRouter()

@chat_router.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = await handle_chat(
        question=request.question,
        user=request.user,
        session_id=request.session_id,
        db=db,
    )
    return ChatResponse(**result)


@chat_router.get("/api/history/{session_id}", response_model=List[HistoryItem], tags=["history"])
def history(session_id: str, db: Session = Depends(get_db)) -> List[HistoryItem]:
    return get_history(session_id=session_id, db=db)


@chat_router.get("/api/sessions/{user}", response_model=UserSessionsResponse, tags=["history"])
def sessions_by_user(user: str, db: Session = Depends(get_db)) -> UserSessionsResponse:
    session_ids = get_sessions(user=user, db=db)
    return UserSessionsResponse(user=user, sessions=[str(s) for s in session_ids])


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


@chat_router.post("/api/chat/stream", tags=["chat"])
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Chat con eventos en vivo (Server-Sent Events). Usa su propia sesión de BD:
    la dependencia get_db se cierra antes de que termine un StreamingResponse."""

    async def gen():
        db = SessionLocal()
        try:
            async for event in AgentService(db).chat_stream(request.question, request.user, request.session_id):
                yield _sse(event)
        finally:
            db.close()

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
