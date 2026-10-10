import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import SessionModel, MessageModel
from app.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    MessageResponse,
    PaginatedMessagesResponse
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: Optional[SessionCreate] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new chat session.
    """
    title = payload.title if payload and payload.title else "New Conversation"
    session_obj = SessionModel(title=title)
    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)

    return SessionResponse(
        id=session_obj.id,
        title=session_obj.title,
        created_at=session_obj.created_at,
        updated_at=session_obj.updated_at,
        message_count=0
    )

@router.get("", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="Max sessions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists chat sessions ordered by latest activity (updated_at DESC).
    """
    # Total count query
    count_stmt = select(func.count()).select_from(SessionModel)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Query sessions with message count
    stmt = (
        select(
            SessionModel,
            func.count(MessageModel.id).label("msg_count")
        )
        .outerjoin(MessageModel, SessionModel.id == MessageModel.session_id)
        .group_by(SessionModel.id)
        .order_by(SessionModel.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    sessions_res = [
        SessionResponse(
            id=sess.id,
            title=sess.title,
            created_at=sess.created_at,
            updated_at=sess.updated_at,
            message_count=msg_cnt
        )
        for sess, msg_cnt in rows
    ]

    return SessionListResponse(
        total=total,
        sessions=sessions_res
    )

@router.get("/{session_id}", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves metadata for a specific chat session by UUID.
    """
    stmt = (
        select(
            SessionModel,
            func.count(MessageModel.id).label("msg_count")
        )
        .outerjoin(MessageModel, SessionModel.id == MessageModel.session_id)
        .where(SessionModel.id == session_id)
        .group_by(SessionModel.id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    sess, msg_cnt = row
    return SessionResponse(
        id=sess.id,
        title=sess.title,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        message_count=msg_cnt
    )

@router.patch("/{session_id}", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def update_session_title(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the title of a specific chat session.
    """
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    result = await db.execute(stmt)
    sess = result.scalar_one_or_none()

    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    sess.title = payload.title
    await db.commit()
    await db.refresh(sess)

    # Get message count
    count_stmt = select(func.count(MessageModel.id)).where(MessageModel.session_id == session_id)
    count_res = await db.execute(count_stmt)
    msg_cnt = count_res.scalar_one()

    return SessionResponse(
        id=sess.id,
        title=sess.title,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        message_count=msg_cnt
    )

@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a session and cascades deletion to linked messages and artifacts.
    """
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    result = await db.execute(stmt)
    sess = result.scalar_one_or_none()

    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    await db.delete(sess)
    await db.commit()

    return {
        "status": "success",
        "message": f"Session '{session_id}' and all dependent records deleted successfully."
    }

@router.get("/{session_id}/messages", response_model=PaginatedMessagesResponse, status_code=status.HTTP_200_OK)
async def get_session_messages(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100, description="Max messages to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns paginated messages for a session in chronological order (created_at ASC).
    """
    # Verify session exists
    sess_stmt = select(SessionModel).where(SessionModel.id == session_id)
    sess_res = await db.execute(sess_stmt)
    if not sess_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    # Count total messages for this session
    count_stmt = select(func.count(MessageModel.id)).where(MessageModel.session_id == session_id)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Query paginated messages in chronological order (created_at ASC)
    msg_stmt = (
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    msg_responses = [
        MessageResponse.model_validate(msg) for msg in messages
    ]

    return PaginatedMessagesResponse(
        session_id=session_id,
        total=total,
        limit=limit,
        offset=offset,
        messages=msg_responses
    )
