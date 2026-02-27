"""
Database persistence helpers for writing records to PostgreSQL.
These are used by handlers and tasks to persist data that was
previously only defined in models but never written.
"""
import logging
from sqlalchemy import select
from app.db.postgres import AsyncSessionLocal
from app.db.models import VideoRecord, QAHistory

logger = logging.getLogger(__name__)


async def save_video_record(video_id: str, title: str, summary: str):
    """Save or update a video record in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        # Check if record already exists
        result = await session.execute(
            select(VideoRecord).where(VideoRecord.video_id == video_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.title = title
            existing.summary = summary
        else:
            record = VideoRecord(video_id=video_id, title=title, summary=summary)
            session.add(record)
        
        await session.commit()


async def save_qa_history(user_id: str, video_id: str, question: str, answer: str, language: str = "english"):
    """Save a Q&A interaction to PostgreSQL for analytics."""
    async with AsyncSessionLocal() as session:
        record = QAHistory(
            user_id=str(user_id),
            video_id=video_id,
            question=question,
            answer=answer,
            language=language
        )
        session.add(record)
        await session.commit()
