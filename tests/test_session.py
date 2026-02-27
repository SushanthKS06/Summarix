import pytest
import json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestSessionManagement:
    """Test Redis-backed session operations."""
    
    async def test_set_and_get_language(self, mock_redis):
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import set_user_language, get_user_language
            
            await set_user_language(123, "Hindi")
            mock_redis.hset.assert_called_with("session:123", "language", "Hindi")
    
    async def test_get_default_language(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=None)
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import get_user_language
            
            lang = await get_user_language(123)
            assert lang == "english"
    
    async def test_set_and_get_video(self, mock_redis):
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import set_current_video
            
            await set_current_video(123, "dQw4w9WgXcQ")
            mock_redis.hset.assert_called_with("session:123", "current_video", "dQw4w9WgXcQ")
    
    async def test_get_no_video(self, mock_redis):
        mock_redis.hget = AsyncMock(return_value=None)
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import get_current_video
            
            video = await get_current_video(123)
            assert video is None
    
    async def test_add_conversation_history(self, mock_redis):
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import add_to_conversation_history
            
            await add_to_conversation_history(123, "abc", "What is ML?", "ML is...")
            mock_redis.rpush.assert_called_once()
            mock_redis.ltrim.assert_called_once()
            mock_redis.expire.assert_called_once()
    
    async def test_get_conversation_history(self, mock_redis):
        history_data = [
            json.dumps({"question": "Q1", "answer": "A1"}),
            json.dumps({"question": "Q2", "answer": "A2"}),
        ]
        mock_redis.lrange = AsyncMock(return_value=history_data)
        
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import get_conversation_history
            
            history = await get_conversation_history(123, "abc")
            assert len(history) == 2
            assert history[0]["question"] == "Q1"
            assert history[1]["answer"] == "A2"
    
    async def test_clear_conversation_history(self, mock_redis):
        with patch("app.bot.session.get_redis", return_value=mock_redis):
            from app.bot.session import clear_conversation_history
            
            await clear_conversation_history(123, "abc")
            mock_redis.delete.assert_called_with("history:123:abc")
