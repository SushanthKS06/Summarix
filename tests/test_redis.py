import pytest
import json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestRedisCache:
    """Test Redis caching operations."""
    
    async def test_cache_and_get_transcript(self, mock_redis):
        transcript = [{"text": "hello", "start": 0.0}]
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import cache_transcript, get_cached_transcript
            
            await cache_transcript("abc123", transcript)
            mock_redis.setex.assert_called_once()
            
            # Verify the key format and TTL
            call_args = mock_redis.setex.call_args
            assert "transcript:abc123" in str(call_args)
    
    async def test_get_cached_transcript_miss(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import get_cached_transcript
            
            result = await get_cached_transcript("nonexistent")
            assert result is None
    
    async def test_get_cached_transcript_hit(self, mock_redis):
        transcript = [{"text": "hello", "start": 0.0}]
        mock_redis.get = AsyncMock(return_value=json.dumps(transcript))
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import get_cached_transcript
            
            result = await get_cached_transcript("abc123")
            assert result == transcript
    
    async def test_cache_and_get_summary(self, mock_redis):
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import cache_summary
            
            await cache_summary("abc123", "This is a summary")
            mock_redis.setex.assert_called_once()
    
    async def test_get_cached_summary_hit(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="Cached summary")
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import get_cached_summary
            
            result = await get_cached_summary("abc123")
            assert result == "Cached summary"


@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting operations."""
    
    async def test_first_request_allowed(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import check_rate_limit
            
            allowed = await check_rate_limit(123, "video", 5, 3600)
            assert allowed is True
    
    async def test_within_limit_allowed(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="3")
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import check_rate_limit
            
            allowed = await check_rate_limit(123, "video", 5, 3600)
            assert allowed is True
    
    async def test_at_limit_denied(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="5")
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import check_rate_limit
            
            allowed = await check_rate_limit(123, "video", 5, 3600)
            assert allowed is False
    
    async def test_over_limit_denied(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="10")
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import check_rate_limit
            
            allowed = await check_rate_limit(123, "video", 5, 3600)
            assert allowed is False
    
    async def test_get_remaining(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="2")
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import get_rate_limit_remaining
            
            remaining = await get_rate_limit_remaining(123, "video", 5)
            assert remaining == 3
    
    async def test_get_remaining_no_usage(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        
        with patch("app.db.redis_client.get_redis", return_value=mock_redis):
            from app.db.redis_client import get_rate_limit_remaining
            
            remaining = await get_rate_limit_remaining(123, "video", 5)
            assert remaining == 5
