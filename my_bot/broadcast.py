import asyncio
import logging
from config import BROADCAST_PAUSE_MS
import storage

async def broadcast(bot, topic: str, text: str):
    ids = storage.list_subscribers(topic)
    delivered = 0
    failed = 0
    
    for user_id in ids:
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            delivered += 1
        except Exception as e:
            failed += 1
            logging.error(f"Розсилка: не вдалося надіслати {user_id}: {e}")
            if "forbidden" in str(e).lower() or "blocked" in str(e).lower():
                try:
                    storage.remove_subscriber(topic, user_id)
                except Exception as se:
                    logging.error(f"Не вдалося прибрати підписника: {se}")
                    
        await asyncio.sleep(BROADCAST_PAUSE_MS / 1000.0)
        
    return {"delivered": delivered, "failed": failed}