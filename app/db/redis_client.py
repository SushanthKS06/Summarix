import json
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

async def get_redis():
    return redis_client

# ── Transcript Caching (24h TTL) ───────────────────────────────────────────

TRANSCRIPT_CACHE_PREFIX = "transcript:"
TRANSCRIPT_TTL = 86400  # 24 hours

async def cache_transcript(video_id: str, transcript: list[dict]):
    """Cache transcript data in Redis with 24h TTL."""
    r = await get_redis()
    await r.setex(
        f"{TRANSCRIPT_CACHE_PREFIX}{video_id}",
        TRANSCRIPT_TTL,
        json.dumps(transcript)
    )

async def get_cached_transcript(video_id: str) -> list[dict] | None:
    """Retrieve cached transcript, returns None on miss."""
    r = await get_redis()
    data = await r.get(f"{TRANSCRIPT_CACHE_PREFIX}{video_id}")
    if data:
        return json.loads(data)
    return None

# ── Summary Caching (24h TTL) ──────────────────────────────────────────────

SUMMARY_CACHE_PREFIX = "summary:"
SUMMARY_TTL = 86400  # 24 hours

async def cache_summary(video_id: str, summary: str):
    """Cache generated summary in Redis."""
    r = await get_redis()
    await r.setex(f"{SUMMARY_CACHE_PREFIX}{video_id}", SUMMARY_TTL, summary)

async def get_cached_summary(video_id: str) -> str | None:
    """Retrieve cached summary, returns None on miss."""
    r = await get_redis()
    return await r.get(f"{SUMMARY_CACHE_PREFIX}{video_id}")

# ── Rate Limiting (Atomic Lua Script) ──────────────────────────────────────

RATE_LIMIT_PREFIX = "ratelimit:"

# Lua script for atomic check-and-increment — eliminates TOCTOU race condition
# Returns 1 if allowed, 0 if denied
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local max_count = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = tonumber(redis.call('GET', key) or '0')
if current >= max_count then
    return 0
end

local new_count = redis.call('INCR', key)
if new_count == 1 then
    redis.call('EXPIRE', key, window)
end
return 1
"""

# Pre-registered script reference (set on first call)
_rate_limit_script = None

async def check_rate_limit(user_id: int, action: str, max_count: int, window_seconds: int) -> bool:
    """
    Atomic rate limiter using a Lua script.
    Returns True if the user is within the rate limit, False if exceeded.
    The check and increment happen in a single atomic Redis operation.
    """
    global _rate_limit_script
    r = await get_redis()
    key = f"{RATE_LIMIT_PREFIX}{action}:{user_id}"
    
    if _rate_limit_script is None:
        _rate_limit_script = r.register_script(_RATE_LIMIT_LUA)
    
    result = await _rate_limit_script(keys=[key], args=[max_count, window_seconds])
    return bool(result)

async def get_rate_limit_remaining(user_id: int, action: str, max_count: int) -> int:
    """Get remaining requests for a user in the current window."""
    r = await get_redis()
    key = f"{RATE_LIMIT_PREFIX}{action}:{user_id}"
    count = await r.get(key)
    if count is None:
        return max_count
    return max(0, max_count - int(count))
