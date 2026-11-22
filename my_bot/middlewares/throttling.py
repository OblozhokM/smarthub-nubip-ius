import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        super().__init__()
        self.limit = limit
        self.user_timestamps = {}

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()
        last_time = self.user_timestamps.get(user_id, 0)

        if now - last_time < self.limit:
            logging.warning(f"⚠️ Спам від користувача {user_id}. Запит пропущено.")
            await event.answer("⚠️ Забагато запитів! Зачекайте секунду перед наступною командою.")
            return

        self.user_timestamps[user_id] = now
        return await handler(event, data)