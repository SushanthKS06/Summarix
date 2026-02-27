"""
Shared LLM client with built-in retry logic for Groq API rate limits.
Both llm.py and translation.py import from this module instead of
creating their own ChatGroq instances.
"""
import logging
import asyncio
from langchain_groq import ChatGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.0
)


async def invoke_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Invoke the LLM with automatic retry on rate-limit (429) errors.
    
    Uses exponential backoff: 2s, 4s, 8s between retries.
    Returns the response content string.
    """
    for attempt in range(max_retries + 1):
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "limit" in error_str
            
            if is_rate_limit and attempt < max_retries:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Groq rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            
            if is_rate_limit:
                logger.error(f"Groq rate limit exceeded after {max_retries} retries: {e}")
                raise ValueError("⏳ AI service is temporarily busy. Please try again in a few seconds.")
            
            logger.error(f"LLM invocation error: {e}")
            raise
