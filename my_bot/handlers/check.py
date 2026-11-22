import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards import BTN_CHECKIN
from utils.validators import (
    parse_number,
    parse_id,
    parse_hours,
    parse_count,
    parse_minutes,
    is_valid_date,
    validate_qr_code
)
from utils.format import (
    NOT_FOUND_TEXT,
    SAVE_FAILED_TEXT,
    format_booking,
    format_ago,
    format_reminder,
    format_weather,
    format_import_report,
    format_period_report,
    format_stats_report
)
from utils.csv_parser import read_csv_file, bookings_from_csv
from config import IMPORT_FILE, REPORT_TIME, TOPICS, ADMIN_ID, DEFAULT_CITY
from broadcast import broadcast
from aiogram.types import BufferedInputFile
from utils import chart
import config
from alerts import check_reading
import weather as weather_service
import storage

router = Router()
MAX_IMPORT = 500

def is_topic(name: str) -> bool:
    return name in TOPICS

def topics_text() -> str:
    return "\n".join([f"• `{t}` — {desc}" for t, desc in TOPICS.items()])

# ==========================================
# 1. ЗОВНІШНІЙ API ПОГОДИ (Лабораторна №16)
# ==========================================

@router.message(Command("weather"))
async def weather_handler(message: types.Message):
    """Отримання поточної погоди у вказаному місті."""
    parts = message.text.split(maxsplit=1)
    city = parts[1].strip() if len(parts) > 1 else DEFAULT_CITY
    
    if len(city) > 50:
        await message.answer("⚠️ Назва міста занадто довга (до 50 символів).")
        return
        
    try:
        w = await weather_service.weather_for_city(city)
        if w is None:
            await message.answer(f"⚠️ Місто «{city}» не знайдено.")
            return
        await message.answer(format_weather(w), parse_mode="Markdown")
    except Exception as e:
        await message.answer("❌ Не вдалося отримати погоду. Спробуйте пізніше.")

@router.message(Command("compare"))
async def compare_handler(message: types.Message):
    """Порівняння тривалості останнього бронювання з температурою надворі."""
    latest = storage.list_bookings()
    if not latest:
        await message.answer("📋 Бронювань ще немає. Додайте перше: `/add 1 2`", parse_mode="Markdown")
        return
        
    rec = latest[0]
    try:
        w = await weather_service.weather_for_city(DEFAULT_CITY)
        if w is None:
            await message.answer("⚠️ Не вдалося отримати погоду для порівняння.")
            return
            
        diff = rec["hours"] - w["temperature"]
        msg = (
            f"🌡 **Порівняння з погодою у м. {w['city']}:**\n"
            f"• Погода надворі: `{w['temperature']} °C`\n"
            f"• Останнє бронювання: `{rec['hours']} год` (Стіл №{rec['tableNum']})\n"
            f"• Різниця показників: `{diff:.1f}`"
        )
        await message.answer(msg, parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Не вдалося отримати дані погоди.")

# ==========================================
# 2. ТЕМИ ПІДПИСОК ТА РОЗСИЛКА (Лабораторна №15)
# ==========================================

@router.message(Command("id"))
async def id_handler(message: types.Message):
    await message.answer(f"👤 Твій Telegram ID: `{message.from_user.id}`", parse_mode="Markdown")

@router.message(Command("subscriptions"))
async def subscriptions_handler(message: types.Message):
    user_id = message.from_user.id
    text = "📋 **Твої підписки:**\n"
    for t, desc in TOPICS.items():
        mark = "✔" if storage.is_subscribed(t, user_id) else "✖"
        text += f"\n{mark} `{t}` — {desc}"
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("subscribe"))
async def subscribe_handler(message: types.Message):
    parts = message.text.split()
    topic = parts[1] if len(parts) > 1 else None
    if not topic or not is_topic(topic):
        await message.answer("⚠️ Формат: `/subscribe <тема>`.\n\n**Доступні теми:**\n" + topics_text(), parse_mode="Markdown")
        return
    try:
        storage.add_subscriber(topic, message.from_user.id)
        await message.answer(f"✅ Підписано: {TOPICS[topic]}.", parse_mode="Markdown")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("unsubscribe"))
async def unsubscribe_handler(message: types.Message):
    parts = message.text.split()
    topic = parts[1] if len(parts) > 1 else None
    if not topic or not is_topic(topic):
        await message.answer("⚠️ Формат: `/unsubscribe <тема>`.\n\n**Доступні теми:**\n" + topics_text(), parse_mode="Markdown")
        return
    try:
        storage.remove_subscriber(topic, message.from_user.id)
        await message.answer(f"🔔 Відписано: {TOPICS[topic]}.", parse_mode="Markdown")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("broadcast"))
async def broadcast_handler(message: types.Message, bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ця команда лише для адміністратора.")
        return
        
    parts = message.text.split(maxsplit=1)
    text = parts[1].strip() if len(parts) > 1 else ""
    if not text or len(text) > 1000:
        await message.answer("⚠️ Формат: `/broadcast <текст>` (до 1000 символів).", parse_mode="Markdown")
        return
        
    total = len(storage.list_subscribers("news"))
    await message.answer(f"📢 Розсилку запущено. Підписників теми news: {total}")
    
    result = await broadcast(bot, "news", f"📢 {text}")
    await message.answer(f"✅ Розсилку завершено.\n• Доставлено: {result['delivered']}\n• Помилок: {result['failed']}")

# ==========================================
# 3. ПЛАНИВАЛЬНИК ТА НАГАДУВАННЯ (Лабораторна №14)
# ==========================================

@router.message(Command("daily"))
async def daily_handler(message: types.Message):
    try:
        user_id = message.from_user.id
        if storage.is_subscribed("report", user_id):
            storage.remove_subscriber("report", user_id)
            await message.answer("🔔 Щоденний звіт вимкнено.")
        else:
            storage.add_subscriber("report", user_id)
            await message.answer(f"🔔 Щоденний звіт увімкнено: щодня о {REPORT_TIME} за Києвом.")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("remind"))
async def remind_handler(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("⚠️ Формат: `/remind <хвилини> <текст>`", parse_mode="Markdown")
        return
    minutes = parse_minutes(parts[1])
    text = parts[2].strip()
    if minutes is None or not text or len(text) > 200:
        await message.answer("⚠️ Некоректні параметри.")
        return
    due_dt = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    try:
        reminder = storage.add_reminder(message.from_user.id, text, due_dt.isoformat())
        await message.answer("✅ Нагадаю:\n" + format_reminder(reminder), parse_mode="Markdown")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("reminders"))
async def reminders_handler(message: types.Message):
    items = storage.list_user_reminders(message.from_user.id)
    if not items:
        await message.answer("📋 Активних нагадувань немає.", parse_mode="Markdown")
        return
    text = "📋 **Ваші нагадування:**\n" + "\n".join([format_reminder(r) for r in items])
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("delremind"))
async def delremind_handler(message: types.Message):
    parts = message.text.split()
    r_id = parse_id(parts[1]) if len(parts) > 1 else None
    if r_id is None:
        await message.answer("⚠️ Формат: `/delremind <номер_нагадування>`", parse_mode="Markdown")
        return
    user_reminders = storage.list_user_reminders(message.from_user.id)
    target = next((r for r in user_reminders if r["id"] == r_id), None)
    if target is None:
        await message.answer("⚠️ Нагадування не знайдено.")
        return
    try:
        storage.remove_reminder(r_id)
        await message.answer(f"🗑 Видалено: {format_reminder(target)}", parse_mode="Markdown")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

# ==========================================
# 4. АНАЛІТИКА ТА CRUD (з перевіркою аномалій)
# ==========================================

@router.message(Command("add"))
async def add_handler(message: types.Message, bot):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠️ Формат: `/add <номер_столу> <годин>`", parse_mode="Markdown")
        return
    table_num = parse_id(parts[1])
    hours = parse_number(parts[2])
    if table_num is None or hours is None:
        await message.answer("⚠️ Некоректні параметри.")
        return
    try:
        user_name = message.from_user.full_name or "Студент"
        rec = storage.add_booking(message.from_user.id, user_name, table_num, hours)
        await message.answer("✅ Додано бронювання:\n" + format_booking(rec), parse_mode="Markdown")
        check_reading(bot, rec)
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("report"))
async def report_handler(message: types.Message):
    parts = message.text.split()
    param = parts[1] if len(parts) > 1 else None
    hours = parse_hours(param)
    if hours is None:
        await message.answer("⚠️ Формат: `/report <години>`", parse_mode="Markdown")
        return
    records = storage.list_bookings_last_hours(hours)
    await message.answer(format_stats_report(f"За останні {hours} год", records), parse_mode="Markdown")

@router.message(Command("top"))
async def top_handler(message: types.Message):
    parts = message.text.split()
    param = parts[1] if len(parts) > 1 else None
    count = parse_count(param)
    if count is None:
        await message.answer("⚠️ Формат: `/top <кількість>`", parse_mode="Markdown")
        return
    items = storage.list_top_bookings(count)
    if not items:
        await message.answer("📋 Бронювань ще немає.", parse_mode="Markdown")
        return
    text = f"🏆 **ТОП-{len(items)} найтриваліших бронювань:**\n"
    text += "\n".join([format_booking(r) for r in items])
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("time"))
async def time_handler(message: types.Message):
    now_utc = datetime.now(timezone.utc)
    kyiv_tz = timezone(timedelta(hours=2))
    now_kyiv = now_utc.astimezone(kyiv_tz)
    msg = (
        f"🕒 **Поточний час:**\n"
        f"• Київ: `{now_kyiv.strftime('%d.%m.%Y, %H:%M:%S')}`\n"
        f"• UTC (у базі): `{now_utc.isoformat()}`"
    )
    await message.answer(msg, parse_mode="Markdown")

@router.message(Command("last"))
async def last_handler(message: types.Message):
    parts = message.text.split()
    param = parts[1] if len(parts) > 1 else None
    hours = parse_hours(param)
    if hours is None:
        await message.answer("⚠️ Формат: `/last <години>`", parse_mode="Markdown")
        return
    items = storage.list_bookings_last_hours(hours)
    await message.answer(format_period_report(f"За останні {hours} год", items), parse_mode="Markdown")

@router.message(Command("day"))
async def day_handler(message: types.Message):
    parts = message.text.split()
    day_text = parts[1] if len(parts) > 1 else None
    if not day_text or not is_valid_date(day_text):
        await message.answer("⚠️ Формат: `/day ДД.ММ.РРРР`", parse_mode="Markdown")
        return
    items = storage.list_bookings_by_day(day_text)
    await message.answer(format_period_report(f"За {day_text}", items), parse_mode="Markdown")

@router.message(Command("today"))
async def today_handler(message: types.Message):
    kyiv_tz = timezone(timedelta(hours=2))
    today_str = datetime.now(timezone.utc).astimezone(kyiv_tz).strftime("%d.%m.%Y")
    items = storage.list_bookings_by_day(today_str)
    await message.answer(format_period_report(f"За сьогодні ({today_str})", items), parse_mode="Markdown")

@router.message(Command("import"))
async def import_handler(message: types.Message):
    try:
        text = read_csv_file(IMPORT_FILE)
    except Exception:
        await message.answer("❌ Не вдалося прочитати файл імпорту.")
        return
    if text is None:
        await message.answer("⚠️ Файл імпорту не знайдено.", parse_mode="Markdown")
        return
    result = bookings_from_csv(text)
    if len(result["good"]) == 0:
        await message.answer(format_import_report(0, result["errors"]) + "\n❌ Немає коректних рядків.", parse_mode="Markdown")
        return
    if len(result["good"]) > MAX_IMPORT:
        await message.answer(f"⚠️ Забагато записів: {len(result['good'])}.")
        return
    try:
        user_name = message.from_user.full_name or "Студент"
        storage.add_many_bookings(message.from_user.id, user_name, result["good"])
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)
        return
    await message.answer(format_import_report(len(result["good"]), result["errors"]), parse_mode="Markdown")

@router.message(Command("list"))
async def list_handler(message: types.Message):
    items = storage.list_bookings()
    if not items:
        await message.answer("📋 Бронювань ще немає.", parse_mode="Markdown")
        return
    text = "📋 **Останні бронювання:**\n" + "\n".join([format_booking(r) for r in items])
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("get"))
async def get_handler(message: types.Message):
    parts = message.text.split()
    b_id = parse_id(parts[1]) if len(parts) > 1 else None
    if b_id is None:
        await message.answer("⚠️ Формат: `/get <номер_броні>`", parse_mode="Markdown")
        return
    rec = storage.get_booking(b_id)
    if rec is None:
        await message.answer(NOT_FOUND_TEXT)
        return
    await message.answer(format_booking(rec), parse_mode="Markdown")

@router.message(Command("edit"))
async def edit_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠️ Формат: `/edit <номер_броні> <нові_години>`", parse_mode="Markdown")
        return
    b_id = parse_id(parts[1])
    hours = parse_number(parts[2])
    if b_id is None or hours is None:
        await message.answer("⚠️ Формат: `/edit <номер_броні> <нові_години>`", parse_mode="Markdown")
        return
    try:
        rec = storage.update_booking(b_id, hours)
        if rec is None:
            await message.answer(NOT_FOUND_TEXT)
            return
        await message.answer("✏️ **Оновлено:**\n" + format_booking(rec), parse_mode="Markdown")
    except Exception:
        await message.answer(SAVE_FAILED_TEXT)

@router.message(Command("del"))
async def del_handler(message: types.Message, state: FSMContext):
    parts = message.text.split()
    b_id = parse_id(parts[1]) if len(parts) > 1 else None
    if b_id is None:
        await message.answer("⚠️ Формат: `/del <номер_броні>`", parse_mode="Markdown")
        return
    rec = storage.get_booking(b_id)
    if rec is None:
        await message.answer(NOT_FOUND_TEXT)
        return
    await state.set_state("confirm_delete")
    await state.update_data(delete_id=b_id)
    await message.answer(f"❓ **Видалити бронювання?**\n{format_booking(rec)}\n\nНапишіть **так** або /cancel.", parse_mode="Markdown")

@router.message(Command("check"))
async def check_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Введіть: /check [відсоток] [година]")
        return
    occ = parse_number(parts[1])
    hr = parse_number(parts[2]) if len(parts) >= 3 else 14.0
    if occ is None or hr is None or not (0 <= occ <= 100) or not (0 <= hr <= 23):
        await message.answer("⚠️ Вкажіть коректні числа.")
        return
    if occ > 80.0 and hr >= 18.0:
        res = "🔥 Критичний вечірній пік!"
    elif occ <= 30.0:
        res = "🟢 Низька завантаженість."
    elif occ <= 70.0:
        res = "🟡 Оптимальна завантаженість."
    else:
        res = "🔴 Висока завантаженість."
    await message.answer(res)

@router.message(Command("checkin"))
@router.message(F.text == BTN_CHECKIN)
async def checkin_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not validate_qr_code(parts[1]):
        await message.answer("📲 Введіть код у форматі HUB-XX")
        return
    await message.answer(f"✅ Присутність підтверджено для {parts[1].upper()}!")

@router.message(Command("live"))
async def live_handler(message: types.Message):
    """Показує останні показання від усіх датчиків."""
    latest = storage.latest_by_sensor()
    if not latest:
        await message.answer("📋 Показань ще немає. Запусти симулятор: `python simulator.py 2`", parse_mode="Markdown")
        return
        
    text = "📡 **Останні показання датчиків:**\n"
    for sensor_name, rec in latest.items():
        ago = format_ago(rec.get("createdAt"))
        ago_text = f" ({ago})" if ago else ""
        text += f"\n• **{sensor_name}**: `{rec.get('hours')} °C`{ago_text}"
        
    await message.answer(text, parse_mode="Markdown")

def _parse_hours(raw: str):
    try:
        h = float(raw)
        return h if 0 < h <= 720 else None
    except Exception:
        return None

def _points_for(hours: float, sensor: str) -> dict:
    records = storage.list_readings_last_hours(hours)
    if not sensor and records:
        counts = {}
        for r in records:
            counts[r["sensor"]] = counts.get(r["sensor"], 0) + 1
        valid_sensors = [s for s, c in counts.items() if c >= 2]
        sensor = valid_sensors[0] if valid_sensors else records[0]["sensor"]
    points = []
    for rec in reversed(records):
        if rec["sensor"] == sensor:
            dt = datetime.fromisoformat(rec["createdAt"].replace("Z", "+00:00"))
            points.append({"time": dt.timestamp() * 1000.0, "value": rec["value"]})
    return {"sensor": sensor, "points": points}

@router.message(Command("trend"))
async def trend_handler(message: types.Message):
    parts = (message.text or "").split()
    hours = _parse_hours(parts[1]) if len(parts) > 1 else None
    if hours is None:
        await message.answer("Формат: `/trend <години> <датчик>`, наприклад `/trend 6 зона-1` (від 0 до 720 годин).", parse_mode="Markdown")
        return

    sensor_arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
    found = _points_for(hours, sensor_arg)
    if len(found["points"]) < 2:
        await message.answer("Для діаграми потрібно щонайменше 2 показання датчика за цей період.")
        return

    groups = chart.downsample(found["points"], 30)
    vals = [p["value"] for p in groups]
    v_min = min(p["value"] for p in found["points"])
    v_max = max(p["value"] for p in found["points"])

    await message.answer(
        f"{found['sensor']} (за {hours:g} год, показань: {len(found['points'])})\n"
        f"{chart.sparkline(vals)}\n"
        f"мін {v_min:.1f} · макс {v_max:.1f}"
    )

@router.message(Command("chart"))
async def chart_handler(message: types.Message):
    parts = (message.text or "").split()
    hours = _parse_hours(parts[1]) if len(parts) > 1 else 24.0
    if hours is None:
        await message.answer("Формат: `/chart <години> <датчик>`, наприклад `/chart 6 зона-1` (від 0 до 720 годин).", parse_mode="Markdown")
        return

    sensor_arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
    found = _points_for(hours, sensor_arg)
    if len(found["points"]) < 2:
        await message.answer("Для графіка потрібно щонайменше 2 показання датчика за цей період.")
        return

    pts = chart.downsample(found["points"], 300)
    png_bytes = chart.chart_to_png(
        pts, {"min": config.SENSOR_MIN, "max": config.SENSOR_MAX}
    )
    photo = BufferedInputFile(png_bytes, filename="chart.png")

    try:
        await message.answer_photo(
            photo=photo,
            caption=(
                f"{found['sensor']} · за {hours:g} год · показань: {len(found['points'])}\n"
                "Зелений маркер — мінімум, червоний — максимум; помаранчевий пунктир — межі норми."
            ),
        )
    except Exception as e:
        logging.error(f"Chart send error: {e}")
        await message.answer("Не вдалося надіслати графік. Спробуй пізніше.")