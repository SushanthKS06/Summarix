from app.core.celery_app import celery_app
from app.services.youtube import fetch_transcript, get_full_text, fetch_video_title, extract_timestamp_sections
from app.services.llm import generate_summary
from app.rag.chunking import chunk_transcript
from app.rag.vector_store import VectorStore
from app.db.redis_client import (
    cache_transcript, get_cached_transcript,
    cache_summary, get_cached_summary
)
from app.db.persistence import save_video_record
import asyncio
import logging

logger = logging.getLogger(__name__)

_task_loop = None

def run_async(coro):
    """Utility to run async functions in synchronous Celery tasks.
    
    Reuses a single event loop per worker thread to avoid
    'Event loop is closed' errors with async Redis connections.
    """
    global _task_loop
    if _task_loop is None or _task_loop.is_closed():
        _task_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_task_loop)
    return _task_loop.run_until_complete(coro)

@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, video_id: str):
    """
    1. Check cache for transcript + summary
    2. Fetch transcript (if not cached)
    3. Chunk and Embedding -> VectorStore
    4. Generate Summary (if not cached)
    5. Cache everything for future use
    6. Persist to PostgreSQL
    """
    try:
        logger.info(f"Starting processing for video: {video_id}")
        
        # ── Check summary cache first (fastest path) ────────────────────
        cached_summary_text = run_async(get_cached_summary(video_id))
        
        # Also check if FAISS index already exists (embeddings done)
        vector_store = VectorStore(video_id=video_id)
        embeddings_exist = vector_store.index.ntotal > 0
        
        if cached_summary_text and embeddings_exist:
            logger.info(f"Full cache hit for video: {video_id}")
            # Fetch title for the response
            title = run_async(fetch_video_title(video_id))
            return {"status": "success", "summary": cached_summary_text, "title": title, "cached": True}
        
        # ── Fetch transcript (with cache) ────────────────────────────────
        transcript_dicts = run_async(get_cached_transcript(video_id))
        if transcript_dicts:
            logger.info(f"Transcript cache hit for video: {video_id}")
        else:
            logger.info(f"Fetching transcript for video: {video_id}")
            transcript_dicts = run_async(fetch_transcript(video_id))
            if not transcript_dicts:
                return {"status": "error", "message": "Transcript is empty or unavailable."}
            # Cache transcript for 24h
            run_async(cache_transcript(video_id, transcript_dicts))
            
        full_text = get_full_text(transcript_dicts)
        
        # ── RAG Pipeline: Chunking and Embedding ────────────────────────
        if not embeddings_exist:
            logger.info(f"Chunking transcript for {video_id}")
            chunks = chunk_transcript(transcript_dicts)
            
            logger.info(f"Storing embeddings for {video_id} in FAISS")
            vector_store.add_chunks(chunks)
        
        # ── Fetch real video title ──────────────────────────────────────
        title = run_async(fetch_video_title(video_id))
        logger.info(f"Video title: {title}")
        
        # ── Extract real timestamps for summary ─────────────────────────
        timestamp_sections = extract_timestamp_sections(transcript_dicts)
        
        # ── Generate Summary (with cache) ────────────────────────────────
        if cached_summary_text:
            summary = cached_summary_text
        else:
            logger.info(f"Generating summary for {video_id}")
            summary = run_async(generate_summary(
                full_text, 
                video_title=title,
                timestamp_sections=timestamp_sections
            ))
            # Cache summary for 24h
            run_async(cache_summary(video_id, summary))
        
        # ── Persist to PostgreSQL ────────────────────────────────────────
        try:
            run_async(save_video_record(video_id, title, summary))
            logger.info(f"Saved video record to PostgreSQL for {video_id}")
        except Exception as db_err:
            # Don't fail the task if DB persistence fails
            logger.warning(f"Failed to persist video record to PostgreSQL: {db_err}")
        
        logger.info(f"Processing complete for {video_id}")
        return {"status": "success", "summary": summary, "title": title, "cached": False}
        
    except ValueError as val_err:
        logger.error(f"Value Error processing video {video_id}: {str(val_err)}")
        return {"status": "error", "message": str(val_err)}
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
        # Retry with exponential backoff on unexpected failure
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
