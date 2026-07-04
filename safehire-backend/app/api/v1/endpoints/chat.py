from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.schemas import ChatMessageRequest, ChatMessageResponse
from app.services.chat import generate_chatbot_response

router = APIRouter()

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await generate_chatbot_response(
        message=request.message,
        job_check_id=request.job_check_id,
        db=db
    )
    return result
