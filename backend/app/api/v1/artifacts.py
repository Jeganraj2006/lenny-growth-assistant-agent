import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import SessionModel, ArtifactModel
from app.schemas.artifact import ArtifactResponse, ArtifactListResponse

router = APIRouter(tags=["Artifacts"])

@router.get("/sessions/{session_id}/artifacts", response_model=ArtifactListResponse, status_code=status.HTTP_200_OK)
async def list_session_artifacts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all saved artifacts (essays, rendered content) for a chat session.
    """
    # Verify session exists
    sess_stmt = select(SessionModel).where(SessionModel.id == session_id)
    sess_res = await db.execute(sess_stmt)
    if not sess_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    stmt = (
        select(ArtifactModel)
        .where(ArtifactModel.session_id == session_id)
        .order_by(ArtifactModel.created_at.desc())
    )
    result = await db.execute(stmt)
    artifacts = result.scalars().all()

    artifact_responses = [ArtifactResponse.model_validate(art) for art in artifacts]

    return ArtifactListResponse(
        session_id=session_id,
        total=len(artifact_responses),
        artifacts=artifact_responses
    )

@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse, status_code=status.HTTP_200_OK)
async def get_artifact_detail(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves details for a specific artifact by UUID.
    """
    stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
    result = await db.execute(stmt)
    art = result.scalar_one_or_none()

    if not art:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{artifact_id}' not found."
        )

    return ArtifactResponse.model_validate(art)

@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_200_OK)
async def delete_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes an artifact by UUID.
    """
    stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
    result = await db.execute(stmt)
    art = result.scalar_one_or_none()

    if not art:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{artifact_id}' not found."
        )

    await db.delete(art)
    await db.commit()

    return {
        "status": "success",
        "message": f"Artifact '{artifact_id}' deleted successfully."
    }
