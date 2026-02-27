import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import SAMPLE_FULL_TEXT, SAMPLE_SUMMARY


@pytest.mark.asyncio
class TestTranslation:
    """Test translation service."""
    
    async def test_english_passthrough(self):
        from app.services.translation import translate_text
        
        result = await translate_text("Hello world", "english")
        assert result == "Hello world"
    
    async def test_empty_language_passthrough(self):
        from app.services.translation import translate_text
        
        result = await translate_text("Hello world", "")
        assert result == "Hello world"
    
    async def test_none_language_passthrough(self):
        from app.services.translation import translate_text
        
        result = await translate_text("Hello world", None)
        assert result == "Hello world"
    
    async def test_translation_calls_llm(self, mock_llm):
        mock_llm_response = MagicMock()
        mock_llm_response.content = "नमस्ते दुनिया"
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        
        with patch("app.services.translation.llm", mock_llm):
            from app.services.translation import translate_text
            
            result = await translate_text("Hello world", "Hindi")
            assert result == "नमस्ते दुनिया"
            mock_llm.ainvoke.assert_called_once()
    
    async def test_boilerplate_caching(self, mock_llm):
        """Boilerplate strings should be cached after first translation."""
        mock_response = MagicMock()
        mock_response.content = "सोच रहा हूँ..."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.translation.llm", mock_llm):
            # Clear cache for test isolation
            from app.services.translation import translate_text, _boilerplate_cache
            _boilerplate_cache.clear()
            
            # First call should hit LLM
            await translate_text("Thinking...", "Hindi")
            assert mock_llm.ainvoke.call_count == 1
            
            # Second call should use cache
            await translate_text("Thinking...", "Hindi")
            assert mock_llm.ainvoke.call_count == 1  # Still 1, not 2


@pytest.mark.asyncio
class TestLanguageDetection:
    """Test inline language detection."""
    
    async def test_no_language_request(self):
        with patch("app.services.translation.llm") as mock_llm:
            from app.services.translation import detect_language_request
            
            result = await detect_language_request("What is machine learning?")
            assert result is None
            # Should not even call LLM (heuristic catches it)
            mock_llm.ainvoke.assert_not_called()
    
    async def test_explicit_language_request(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "Hindi"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.translation.llm", mock_llm):
            from app.services.translation import detect_language_request
            
            result = await detect_language_request("Summarize in Hindi")
            assert result == "Hindi"
    
    async def test_none_response(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "NONE"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.translation.llm", mock_llm):
            from app.services.translation import detect_language_request
            
            result = await detect_language_request("Explain in detail about pricing")
            # "in" keyword triggers heuristic, but LLM says NONE
            assert result is None
