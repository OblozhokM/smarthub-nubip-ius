import asyncio
import logging
from datetime import datetime, timezone, timedelta
from config import REPORT_TIME
from utils.format import format_stats_report
import storage

def kyiv_time(now_dt: datetime) -> str:
    kyiv_tz = timezone(timedelta(hours=2))
    return now_dt.astimezone(kyiv_tz).strftime("%H:%M")

def kyiv_day(now_dt: datetime) -> str:
    kyiv_tz = timezone(timedelta(hours=2))
    return now_dt.astimezone(kyiv_tz).strftime("%d.%m.%Y")

async def send_safe(bot, user_id: int, text: str):
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Не вдалося надіслати користувачу {user_id}: {e}")
        if "forbidden" in str(e).lower() or "blocked" in str(e).lower():
            try:
                storage.remove_subscriber("report", user_id)
            except Exception as se:
                logging.error(f"Не вдалося прибрати підписника: {se}")

async def check_reminders(bot, now_dt: datetime):
    now_iso = now_dt.isoformat()
    due = storage.list_due_reminders(now_iso)
    for reminder in due:
        storage.remove_reminder(reminder["id"])
        await send_safe(bot, reminder["userId"], f"⏰ **Нагадування:** {reminder['text']}")

async def check_daily_report(bot, now_dt: datetime):
    today = kyiv_day(now_dt)
    if storage.get_last_report_day() == today:
        return
    if kyiv_time(now_dt) < REPORT_TIME:
        return
        
    storage.set_last_report_day(today)
    records = storage.list_bookings_last_hours(24, now_dt)
    text = format_stats_report("Щоденний звіт за 24 години", records)
    
    for user_id in storage.list_subscribers("report"):
        await send_safe(bot, user_id, text)

async def tick(bot):
    now_dt = datetime.now(timezone.utc)
    try:
        await check_reminders(bot, now_dt)
        await check_daily_report(bot, now_dt)
    except Exception as e:
        logging.error(f"Планувальник: {e}")

async def scheduler_loop(bot):
    logging.info("⏰ Планувальник задач успішно запущено!")
    while True:
        await tick(bot)
        await asyncio.sleep(60)