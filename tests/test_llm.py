import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import SAMPLE_FULL_TEXT, SAMPLE_SUMMARY


@pytest.mark.asyncio
class TestLLMService:
    """Test LLM service functions."""
    
    async def test_generate_summary(self, mock_llm):
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import generate_summary
            
            result = await generate_summary(SAMPLE_FULL_TEXT, "Test Video")
            assert result == SAMPLE_SUMMARY
            mock_llm.ainvoke.assert_called_once()
            # Verify prompt includes video title
            call_args = mock_llm.ainvoke.call_args[0][0]
            assert "Test Video" in call_args
    
    async def test_summary_with_default_title(self, mock_llm):
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import generate_summary
            
            await generate_summary(SAMPLE_FULL_TEXT)
            call_args = mock_llm.ainvoke.call_args[0][0]
            assert "Unknown Title" in call_args
    
    async def test_answer_question_without_history(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "Neural networks use activation functions."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import answer_question
            
            result = await answer_question("context here", "What are neural networks?")
            assert result == "Neural networks use activation functions."
            call_args = mock_llm.ainvoke.call_args[0][0]
            assert "No previous conversation" in call_args
    
    async def test_answer_question_with_history(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "Yes, ReLU is common."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        history = [{"question": "What are NNs?", "answer": "Layers of neurons."}]
        
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import answer_question
            
            result = await answer_question("context", "What about activation?", history=history)
            assert result == "Yes, ReLU is common."
            call_args = mock_llm.ainvoke.call_args[0][0]
            assert "What are NNs?" in call_args  # History included
    
    async def test_generate_deepdive(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "🔬 Deep Dive: Neural Networks\n..."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import generate_deepdive
            
            result = await generate_deepdive("context about NNs", "neural networks")
            assert "Deep Dive" in result
            call_args = mock_llm.ainvoke.call_args[0][0]
            assert "neural networks" in call_args
    
    async def test_generate_actionpoints(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "📋 Action Points:\n- [ ] Learn NNs"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("app.services.llm.llm", mock_llm):
            from app.services.llm import generate_actionpoints
            
            result = await generate_actionpoints("context about learning ML")
            assert "Action Points" in result


class TestTokenTruncation:
    """Test token-aware truncation."""
    
    def test_short_text_no_truncation(self):
        from app.services.llm import _truncate_to_tokens
        
        text = "This is a short text."
        result = _truncate_to_tokens(text, max_tokens=100)
        assert result == text
    
    def test_long_text_gets_truncated(self):
        from app.services.llm import _truncate_to_tokens
        
        text = "word " * 50000  # Way more than 12000 tokens
        result = _truncate_to_tokens(text, max_tokens=100)
        assert len(result) < len(text)
    
    def test_truncation_tries_sentence_boundary(self):
        from app.services.llm import _truncate_to_tokens
        
        # Create text with clear sentence boundaries
        text = "First sentence. " * 5000 + "Last sentence."
        result = _truncate_to_tokens(text, max_tokens=50)
        # Should end with a period (sentence boundary)
        assert result.rstrip().endswith(".")
