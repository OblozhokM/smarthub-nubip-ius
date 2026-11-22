import asyncio
import logging
from datetime import datetime

from config import BOOKING_MIN, BOOKING_MAX, SENSOR_MIN, SENSOR_MAX
from utils.format import format_booking
from broadcast import broadcast

# Окремий cooldown для бронювань і датчиків, щоб аномалії не спамили.
_last_alert = {"booking": 0.0, "sensor": 0.0}
COOLDOWN_MS = 10 * 60 * 1000


def _now_ms() -> float:
    return datetime.now().timestamp() * 1000


def _cooldown_ok(kind: str, now_ms: float) -> bool:
    if now_ms - _last_alert.get(kind, 0.0) < COOLDOWN_MS:
        logging.info("⏳ Сповіщення «%s» пропущено (ліміт 10 хв).", kind)
        return False
    _last_alert[kind] = now_ms
    return True


def check_booking_alert(bot, record: dict):
    """Аномалія тривалості бронювання (години)."""
    val = float(record.get("hours", 0.0))
    if BOOKING_MIN <= val <= BOOKING_MAX:
        return
    if not _cooldown_ok("booking", _now_ms()):
        return
    text = (
        "⚠️ **Аномалія бронювання!**\n"
        f"{format_booking(record)}\n"
        f"Допустима тривалість: від {BOOKING_MIN:g} до {BOOKING_MAX:g} год."
    )
    asyncio.create_task(broadcast(bot, "alert", text))


def check_sensor_alert(bot, record: dict):
    """Аномалія показання датчика (температура, °C)."""
    val = float(record.get("hours", 0.0))
    if SENSOR_MIN <= val <= SENSOR_MAX:
        return
    if not _cooldown_ok("sensor", _now_ms()):
        return
    sensor = record.get("userName", "датчик")
    text = (
        "⚠️ **Аномалія показання датчика!**\n"
        f"• Датчик: **{sensor}**\n"
        f"• Значення: `{val:.1f} °C`\n"
        f"• Норма: від {SENSOR_MIN:g} до {SENSOR_MAX:g} °C"
    )
    asyncio.create_task(broadcast(bot, "alert", text))


def check_reading(bot, record: dict):
    """Єдина точка входу: сама визначає тип запису."""
    if record.get("userId") == 0:
        check_sensor_alert(bot, record)
    else:
        check_booking_alert(bot, record)
