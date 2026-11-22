import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router
from ingest import start_ingest_server
from middlewares.throttling import ThrottlingMiddleware
from scheduler import scheduler_loop
from storage import load_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(ThrottlingMiddleware(limit=1.0))
dp.include_router(router)


@dp.error()
async def global_error_handler(event: types.ErrorEvent):
    logging.error("Глобальна помилка: %s", event.exception, exc_info=True)


async def main():
    try:
        load_data()
        asyncio.create_task(scheduler_loop(bot))

        # Запуск HTTP-сервера для отримання показників датчиків
        await start_ingest_server(bot)

        print(">>> SmartHub NUBiP bot started (Lab 10-17).")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Критична помилка запуску: {e}")


if __name__ == "__main__":
    asyncio.run(main())
