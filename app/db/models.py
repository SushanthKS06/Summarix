from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.postgres import Base


class VideoRecord(Base):
    """Track processed videos with metadata."""
    __tablename__ = "video_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(11), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    

class QAHistory(Base):
    """Store Q&A interactions for analytics and history."""
    __tablename__ = "qa_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    video_id = Column(String(11), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    language = Column(String(50), default="english")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
