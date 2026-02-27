import logging
from langchain_core.prompts import PromptTemplate
from app.core.llm_client import invoke_with_retry

logger = logging.getLogger(__name__)

TRANSLATION_PROMPT = PromptTemplate(
    input_variables=["text", "target_language"],
    template="""You are a professional translator. Translate the following text into {target_language}.
Maintain the original formatting perfectly, including emojis, markdown, bullet points, and checkboxes.
Output ONLY the translated text, nothing else.

Text:
{text}

Translation:"""
)

LANGUAGE_DETECTION_PROMPT = PromptTemplate(
    input_variables=["text"],
    template="""Analyze the following user message. If the user is requesting content in a specific language (e.g., "Summarize in Hindi", "Explain in Tamil", "हिंदी में बताओ"), extract the target language name in English.

If the message is just a regular question or not a language request, respond with exactly: NONE

User message: {text}

Language (respond with the language name in English, or NONE):"""
)

# ── Supported Languages ───────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "english", "hindi", "tamil", "telugu", "kannada",
    "marathi", "bengali", "gujarati", "malayalam", "punjabi",
}

def is_supported_language(language: str) -> bool:
    """Check if a language is in the supported list."""
    return language.lower().strip() in SUPPORTED_LANGUAGES

def get_supported_languages_str() -> str:
    """Return a formatted string of supported languages."""
    return ", ".join(lang.title() for lang in sorted(SUPPORTED_LANGUAGES))

# ── Boilerplate Cache ──────────────────────────────────────────────────────
# Cache translated versions of common bot messages to avoid repeated LLM calls
_boilerplate_cache: dict[tuple[str, str], str] = {}

_BOILERPLATE_STRINGS = {
    "Thinking...",
    "Processing video {video_id}... This may take a moment. You will be notified when the summary is ready.",
    "Please send a YouTube video link first before asking questions.",
    "Video data unavailable. Please process the video again.",
    "Invalid YouTube URL. Please make sure it's a valid link.",
    "Error: Process timed out or failed.",
}

def _is_boilerplate(text: str) -> bool:
    """Check if text matches a known boilerplate pattern."""
    for bp in _BOILERPLATE_STRINGS:
        if bp.startswith(text[:20]) or text.startswith(bp[:20]):
            return True
    return False


async def translate_text(text: str, target_language: str) -> str:
    """Translate text to target language with boilerplate caching."""
    if not target_language or target_language.lower() == "english":
        return text
    
    # Check boilerplate cache first
    cache_key = (text, target_language.lower())
    if cache_key in _boilerplate_cache:
        return _boilerplate_cache[cache_key]
        
    prompt = TRANSLATION_PROMPT.format(text=text, target_language=target_language)
    result = await invoke_with_retry(prompt)
    
    # Cache boilerplate translations for reuse
    if _is_boilerplate(text):
        _boilerplate_cache[cache_key] = result
    
    return result


async def detect_language_request(text: str) -> str | None:
    """
    Detect if a user message is requesting content in a specific language.
    Returns the language name (e.g., 'Hindi') or None if not a language request.
    """
    # Quick heuristic check before spending an LLM call
    language_keywords = [
        "in hindi", "in tamil", "in telugu", "in kannada", "in marathi",
        "in bengali", "in gujarati", "in malayalam", "in punjabi",
        "hindi me", "hindi mein", "हिंदी", "தமிழ்", "తెలుగు", "ಕನ್ನಡ",
        "summarize in", "explain in", "translate to", "translate in",
    ]
    
    text_lower = text.lower()
    has_keyword = any(kw in text_lower for kw in language_keywords)
    
    if not has_keyword:
        return None
    
    # Use LLM for precise extraction
    prompt = LANGUAGE_DETECTION_PROMPT.format(text=text)
    result = await invoke_with_retry(prompt)
    result = result.strip()
    
    if result.upper() == "NONE":
        return None
    
    return result
