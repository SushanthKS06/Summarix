import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from app.services.youtube import extract_video_id
from app.bot.tasks import process_video_task
from app.bot.session import (
    set_current_video, get_current_video, 
    set_user_language, get_user_language,
    add_to_conversation_history, get_conversation_history,
    clear_conversation_history
)
from app.services.translation import (
    translate_text, detect_language_request,
    is_supported_language, get_supported_languages_str
)
from app.services.llm import answer_question, generate_deepdive, generate_actionpoints
from app.rag.vector_store import VectorStore
from app.db.redis_client import check_rate_limit, get_rate_limit_remaining
from app.db.persistence import save_qa_history

router = Router()
logger = logging.getLogger(__name__)

# ── Rate Limit Config ──────────────────────────────────────────────────────
VIDEO_RATE_LIMIT = 5          # max videos per window
VIDEO_RATE_WINDOW = 3600      # 1 hour
QUESTION_RATE_LIMIT = 30      # max questions per window
QUESTION_RATE_WINDOW = 3600   # 1 hour
TASK_TIMEOUT = 300            # max seconds to wait for Celery task


WELCOME_MSG = (
    "👋 Welcome to the YouTube AI Assistant!\n\n"
    "Here's what I can do:\n"
    "1️⃣ Send me a YouTube link → get a structured summary\n"
    "2️⃣ /summary <link> → summarize a video\n"
    "3️⃣ Ask me any question about the video\n"
    "4️⃣ /deepdive <topic> → deep analysis of a topic\n"
    "5️⃣ /actionpoints → extract all action items\n"
    "6️⃣ /language <lang> → change output language\n"
    "7️⃣ /help → show this message again\n\n"
    "💡 You can also say things like 'Summarize in Hindi' or 'Explain in Tamil'!\n"
    "🌐 Supported: English, Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Gujarati, Malayalam, Punjabi"
)


@router.message(Command("start"))
async def cmd_start(message: Message):
    lang = await get_user_language(message.from_user.id)
    translated = await translate_text(WELCOME_MSG, lang)
    await message.answer(translated)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Alias for /start — shows available commands."""
    lang = await get_user_language(message.from_user.id)
    translated = await translate_text(WELCOME_MSG, lang)
    await message.answer(translated)


@router.message(Command("language"))
async def cmd_language(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            f"Please specify a language. Example: /language Hindi\n\n"
            f"🌐 Supported languages: {get_supported_languages_str()}"
        )
        return
    
    new_lang = args[1].strip()
    
    # Validate against supported languages
    if not is_supported_language(new_lang):
        await message.answer(
            f"❌ '{new_lang}' is not supported.\n\n"
            f"🌐 Supported languages: {get_supported_languages_str()}"
        )
        return
    
    await set_user_language(message.from_user.id, new_lang)
    await message.answer(f"✅ Language set to **{new_lang}**. All future responses will be in {new_lang}.")


@router.message(Command("summary"))
async def cmd_summary(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Please provide a YouTube link. Example: /summary https://youtube.com/...")
        return
    await process_video_request(message, args[1])


@router.message(Command("deepdive"))
async def cmd_deepdive(message: Message):
    """Deep dive into a specific topic from the current video."""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("Please provide a topic. Example: /deepdive pricing strategy")
        return
    
    video_id = await get_current_video(user_id)
    lang = await get_user_language(user_id)
    
    if not video_id:
        msg = await translate_text("Please send a YouTube video link first before using /deepdive.", lang)
        await message.answer(msg)
        return
    
    # Rate limit check
    allowed = await check_rate_limit(user_id, "question", QUESTION_RATE_LIMIT, QUESTION_RATE_WINDOW)
    if not allowed:
        remaining = await get_rate_limit_remaining(user_id, "question", QUESTION_RATE_LIMIT)
        await message.answer(f"⏳ Rate limit reached. You can ask up to {QUESTION_RATE_LIMIT} questions per hour. Try again later.")
        return
    
    topic = args[1].strip()
    status_msg = await message.answer(await translate_text("🔬 Performing deep dive analysis...", lang))
    
    try:
        # Translate topic to English for retrieval if needed
        if lang.lower() != "english":
            english_topic = await translate_text(topic, "English")
        else:
            english_topic = topic
        
        # Search vector store with more chunks for deep dive
        vector_store = VectorStore(video_id=video_id)
        results = vector_store.search(english_topic, top_k=8)
        
        if not results:
            msg = await translate_text("Video data unavailable. Please process the video again.", lang)
            await status_msg.edit_text(msg)
            return
        
        context_text = "\n\n".join([r['text'] for r in results])
        
        # Generate deep dive
        analysis = await generate_deepdive(context_text, english_topic)
        final = await translate_text(analysis, lang)
        
        await _send_long_message(message, status_msg, final)
    except ValueError as e:
        await status_msg.edit_text(str(e))
    except Exception as e:
        logger.error(f"Deep dive error: {e}")
        await status_msg.edit_text("❌ An error occurred during analysis. Please try again.")


@router.message(Command("actionpoints"))
async def cmd_actionpoints(message: Message):
    """Extract action points from the current video."""
    user_id = message.from_user.id
    video_id = await get_current_video(user_id)
    lang = await get_user_language(user_id)
    
    if not video_id:
        msg = await translate_text("Please send a YouTube video link first before using /actionpoints.", lang)
        await message.answer(msg)
        return
    
    # Rate limit check
    allowed = await check_rate_limit(user_id, "question", QUESTION_RATE_LIMIT, QUESTION_RATE_WINDOW)
    if not allowed:
        await message.answer(f"⏳ Rate limit reached. Try again later.")
        return
    
    status_msg = await message.answer(await translate_text("📋 Extracting action points...", lang))
    
    try:
        # Get all available context
        vector_store = VectorStore(video_id=video_id)
        # Use a broad query to get representative chunks
        results = vector_store.search("main topics actions recommendations steps", top_k=10)
        
        if not results:
            msg = await translate_text("Video data unavailable. Please process the video again.", lang)
            await status_msg.edit_text(msg)
            return
        
        context_text = "\n\n".join([r['text'] for r in results])
        
        # Generate action points
        actionpoints = await generate_actionpoints(context_text)
        final = await translate_text(actionpoints, lang)
        
        await _send_long_message(message, status_msg, final)
    except ValueError as e:
        await status_msg.edit_text(str(e))
    except Exception as e:
        logger.error(f"Action points error: {e}")
        await status_msg.edit_text("❌ An error occurred during extraction. Please try again.")


@router.message(F.text.regexp(r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+'))
async def handle_youtube_link(message: Message):
    await process_video_request(message, message.text)


async def process_video_request(message: Message, url: str):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # ── Rate Limit Check ─────────────────────────────────────────────────
    allowed = await check_rate_limit(user_id, "video", VIDEO_RATE_LIMIT, VIDEO_RATE_WINDOW)
    if not allowed:
        remaining = await get_rate_limit_remaining(user_id, "video", VIDEO_RATE_LIMIT)
        await message.answer(
            f"⏳ Rate limit reached. You can process up to {VIDEO_RATE_LIMIT} videos per hour. "
            f"Try again later."
        )
        return
    
    video_id = extract_video_id(url)
    if not video_id:
        msg = await translate_text("❌ Invalid YouTube URL. Please make sure it's a valid link.", lang)
        await message.answer(msg)
        return
        
    await set_current_video(user_id, video_id)
    # Clear conversation history for the new video
    await clear_conversation_history(user_id, video_id)
    
    processing_msg = await translate_text(
        f"⏳ Processing video `{video_id}`... This may take a moment.", lang
    )
    status_msg = await message.answer(processing_msg)
    
    # Hand off to Celery
    task = process_video_task.delay(video_id)
    
    # ── Non-blocking poll with TIMEOUT ───────────────────────────────────
    elapsed = 0
    poll_interval = 2
    while not task.ready() and elapsed < TASK_TIMEOUT:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    
    if not task.ready():
        error_msg = await translate_text(
            "⏱ Processing is taking too long. The video may be very large. Please try again later.", lang
        )
        await status_msg.edit_text(error_msg)
        return
        
    # task.result may be an exception if the Celery task raised after retries
    result = task.result
    if isinstance(result, Exception):
        logger.error(f"Celery task failed with exception: {result}")
        error_msg = await translate_text(
            f"❌ Processing failed: {str(result)}. Please try again.", lang
        )
        await status_msg.edit_text(error_msg)
        return

    if not result:
        error_msg = await translate_text("❌ Processing failed unexpectedly. Please try again.", lang)
        await status_msg.edit_text(error_msg)
        return
        
    if not isinstance(result, dict):
        logger.error(f"Unexpected task result type: {type(result)}")
        error_msg = await translate_text("❌ Processing failed unexpectedly. Please try again.", lang)
        await status_msg.edit_text(error_msg)
        return

    if result.get("status") == "error":
        error_msg = await translate_text(f"❌ Error: {result.get('message')}", lang)
        await status_msg.edit_text(error_msg)
        return
        
    summary = result.get("summary")
    cached_indicator = " ⚡ (cached)" if result.get("cached") else ""
    translated_summary = await translate_text(summary, lang)
    translated_summary += cached_indicator
    
    await _send_long_message(message, status_msg, translated_summary)


@router.message(F.text)
async def handle_question(message: Message):
    """Fallback handler. Handles questions and inline language detection."""
    user_id = message.from_user.id
    text = message.text
    
    if text.startswith("/"):
        return
    
    lang = await get_user_language(user_id)
    
    # ── Inline Language Detection ────────────────────────────────────────
    detected_lang = await detect_language_request(text)
    if detected_lang:
        # Validate the detected language
        if not is_supported_language(detected_lang):
            await message.answer(
                f"❌ '{detected_lang}' is not supported.\n"
                f"🌐 Supported: {get_supported_languages_str()}"
            )
            return
        
        await set_user_language(user_id, detected_lang)
        lang = detected_lang
        await message.answer(f"🌐 Language switched to **{detected_lang}**!")
        
        # If user also has a video loaded, re-send the summary in new language
        video_id = await get_current_video(user_id)
        if video_id:
            from app.db.redis_client import get_cached_summary
            cached = await get_cached_summary(video_id)
            if cached:
                translated = await translate_text(cached, lang)
                await _send_long_message(message, None, translated)
        return
    
    # ── Q&A Flow ─────────────────────────────────────────────────────────
    video_id = await get_current_video(user_id)
    
    if not video_id:
        msg = await translate_text("📎 Please send a YouTube video link first before asking questions.", lang)
        await message.answer(msg)
        return
    
    # Rate limit check
    allowed = await check_rate_limit(user_id, "question", QUESTION_RATE_LIMIT, QUESTION_RATE_WINDOW)
    if not allowed:
        await message.answer(f"⏳ Rate limit reached ({QUESTION_RATE_LIMIT} questions/hour). Try again later.")
        return
        
    status_msg = await message.answer(await translate_text("🤔 Thinking...", lang))
    
    try:
        if lang.lower() != "english":
            english_question = await translate_text(text, "English")
        else:
            english_question = text
            
        # Search Vector Store
        vector_store = VectorStore(video_id=video_id)
        results = vector_store.search(english_question, top_k=5)
        
        if not results:
            msg = await translate_text("📎 Video data unavailable. Please process the video again.", lang)
            await status_msg.edit_text(msg)
            return
            
        context_text = "\n\n".join([r['text'] for r in results])
        
        # Get conversation history for context-aware answers
        history = await get_conversation_history(user_id, video_id)
        
        # Generate Answer with history
        answer = await answer_question(context_text, english_question, history=history)
        
        # Store in conversation history
        await add_to_conversation_history(user_id, video_id, english_question, answer)
        
        # Persist Q&A to PostgreSQL (non-blocking, don't fail on error)
        try:
            await save_qa_history(str(user_id), video_id, english_question, answer, lang)
        except Exception as db_err:
            logger.warning(f"Failed to persist Q&A to PostgreSQL: {db_err}")
        
        final_answer = await translate_text(answer, lang)
        
        await status_msg.edit_text(final_answer)
    except ValueError as e:
        await status_msg.edit_text(str(e))
    except Exception as e:
        logger.error(f"Q&A error: {e}")
        await status_msg.edit_text("❌ An error occurred. Please try again.")


async def _send_long_message(message: Message, status_msg, text: str):
    """Send long text as multiple messages if exceeding Telegram's 4096 char limit."""
    if len(text) <= 4000:
        if status_msg:
            await status_msg.edit_text(text)
        else:
            await message.answer(text)
    else:
        # Delete the status message and send as multiple parts
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass
        for i in range(0, len(text), 4000):
            await message.answer(text[i:i+4000])
