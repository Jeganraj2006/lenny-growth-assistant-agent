from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.session import MessageResponse
from app.services.chat import process_chat_completion

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_completion_endpoint(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Executes grounded conversational chat completion with persistent message history and citations.
    """
    try:
        user_msg, assistant_msg, citations, provider_used, model_used = await process_chat_completion(
            db_session=db,
            session_id=payload.session_id,
            user_prompt=payload.message,
            provider=payload.provider,
            model=payload.model
        )

        return ChatResponse(
            session_id=payload.session_id,
            user_message=MessageResponse.model_validate(user_msg),
            assistant_message=MessageResponse.model_validate(assistant_msg),
            citations=citations,
            provider_used=provider_used,
            model_used=model_used
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg
            )
        if "api key" in err_msg.lower() or "unconfigured" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=err_msg
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Model provider error: {str(run_err)}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat execution failed: {str(exc)}"
        )
