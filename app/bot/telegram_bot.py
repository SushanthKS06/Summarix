from aiogram import Bot, Dispatcher
from app.core.config import settings
from app.bot.handlers import router

def get_bot() -> Bot:
    return Bot(token=settings.TELEGRAM_TOKEN)
    
def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
