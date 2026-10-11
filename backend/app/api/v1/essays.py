from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.essay import EssayGenerateRequest, EssayGenerateResponse
from app.services.essay import generate_ship30_essay

router = APIRouter(prefix="/essays", tags=["Essays"])

@router.post("/generate", response_model=EssayGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_essay_endpoint(
    payload: EssayGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a Ship 30 for 30 growth essay grounded in transcript evidence
    and stores it as a persistent artifact.
    """
    if payload.format.lower() not in ["markdown", "html"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid artifact format. Supported formats are 'markdown' or 'html'."
        )

    try:
        artifact_obj, citations, provider_used, model_used = await generate_ship30_essay(
            db_session=db,
            session_id=payload.session_id,
            topic=payload.topic,
            output_format=payload.format,
            provider=payload.provider,
            model=payload.model
        )

        words = len(artifact_obj.content.split())
        return EssayGenerateResponse(
            artifact_id=artifact_obj.id,
            session_id=artifact_obj.session_id,
            title=artifact_obj.title,
            format=artifact_obj.format,
            content=artifact_obj.content,
            citations=citations,
            word_count=words,
            target_word_count=1250,
            meets_target=bool(words >= 950),
            provider_used=provider_used,
            model_used=model_used,
            created_at=artifact_obj.created_at
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
            detail=f"Model provider execution failed: {str(run_err)}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Essay generation failed: {str(exc)}"
        )
