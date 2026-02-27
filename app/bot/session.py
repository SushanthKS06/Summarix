import json
from app.db.redis_client import get_redis

# ── Core Session Helpers ───────────────────────────────────────────────────

async def set_user_session(user_id: int, key: str, value: str):
    redis = await get_redis()
    await redis.hset(f"session:{user_id}", key, value)

async def get_user_session(user_id: int, key: str) -> str | None:
    redis = await get_redis()
    return await redis.hget(f"session:{user_id}", key)

# ── Language ───────────────────────────────────────────────────────────────

async def set_user_language(user_id: int, language: str):
    await set_user_session(user_id, "language", language)

async def get_user_language(user_id: int) -> str:
    lang = await get_user_session(user_id, "language")
    return lang or "english"

# ── Current Video ─────────────────────────────────────────────────────────

async def set_current_video(user_id: int, video_id: str):
    await set_user_session(user_id, "current_video", video_id)

async def get_current_video(user_id: int) -> str | None:
    return await get_user_session(user_id, "current_video")

# ── Conversation History (per user per video, last N exchanges) ────────────

MAX_HISTORY = 5

async def add_to_conversation_history(user_id: int, video_id: str, question: str, answer: str):
    """Append a Q&A pair to the user's conversation history for a video."""
    redis = await get_redis()
    key = f"history:{user_id}:{video_id}"
    
    entry = json.dumps({"question": question, "answer": answer})
    await redis.rpush(key, entry)
    # Keep only last N entries
    await redis.ltrim(key, -MAX_HISTORY, -1)
    # Expire after 6 hours
    await redis.expire(key, 21600)

async def get_conversation_history(user_id: int, video_id: str) -> list[dict]:
    """Retrieve conversation history for context-aware Q&A."""
    redis = await get_redis()
    key = f"history:{user_id}:{video_id}"
    
    entries = await redis.lrange(key, 0, -1)
    return [json.loads(e) for e in entries]

async def clear_conversation_history(user_id: int, video_id: str):
    """Clear conversation history when a new video is processed."""
    redis = await get_redis()
    await redis.delete(f"history:{user_id}:{video_id}")
