import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram.types import Update

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.endpoints import router as api_router
from app.db.postgres import init_db
from app.bot.telegram_bot import get_bot, get_dispatcher

logger = logging.getLogger(__name__)
bot = get_bot()
dp = get_dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting up Bot backend...")
    await init_db()
    
    logger.info("Starting Telegram matching polling...")
    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bot backend...")
    polling_task.cancel()
    await bot.session.close()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(api_router, prefix="/api")
