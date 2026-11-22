import copy
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from config import DATA_FILE, DASHBOARD_PERIOD_HOURS, DASHBOARD_ROWS, DASHBOARD_STALE_MS

KYIV_TZ = timezone(timedelta(hours=2))


def _default_data() -> dict:
    return {
        "users": {},
        "bookings": [],
        "lastBookingId": 0,
        "subscriptions": {},
        "reminders": [],
        "lastReminderId": 0,
        "lastReportDay": "",
    }


data = _default_data()


def load_data():
    """Завантажує JSON-базу. Пошкоджений файл не «отруює» стан у пам'яті."""
    global data
    fresh = _default_data()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                fresh.update(loaded)
            data = fresh
            logging.info("✅ Базу даних успішно завантажено.")
        except Exception as e:
            logging.error(f"❌ Помилка завантаження БД: {e}")
            data = fresh
    else:
        data = fresh
        save_data()
    return data


def save_data(new_data=None):
    """Атомарний запис: тимчасовий файл + os.replace."""
    global data
    if new_data is not None:
        data = new_data
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_FILE)


def make_copy() -> dict:
    """Глибока копія поточного стану для пакетних змін."""
    load_data()
    return copy.deepcopy(data)


def save_changes(new_data: dict):
    """Зберігає підготовлену копію (використовується seed.py)."""
    save_data(new_data)
    return data


def _parse_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _is_reading(record: dict) -> bool:
    return record.get("userId") == 0


# --- Користувачі (з попередніх лабораторних) ---
def get_user(user_id: int) -> dict:
    load_data()
    users = data.setdefault("users", {})
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "id": user_id,
            "name": "",
            "phone": "",
            "city": "Київ",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        save_data()
    return users[uid]


def update_user(user_id: int, **kwargs) -> dict:
    user = get_user(user_id)
    user.update(kwargs)
    save_data()
    return user


def save_user(user_id: int, name: str = "", phone: str = "", city: str = "Київ"):
    return update_user(user_id, name=name, phone=phone, city=city)


# --- Бронювання та показання датчиків ---
def add_booking(user_id: int, user_name: str, table_num: int, hours: float):
    load_data()
    data["lastBookingId"] = data.get("lastBookingId", 0) + 1
    record = {
        "id": data["lastBookingId"],
        "userId": user_id,
        "userName": user_name,
        "tableNum": table_num,
        "hours": hours,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    data.setdefault("bookings", []).append(record)
    save_data()
    return record


def add_device_reading(sensor: str, value: float, time_str: str):
    """Додає показання, зберігаючи хронологічний порядок і відсікаючи дублікати."""
    load_data()
    readings = data.setdefault("bookings", [])

    # Дублікат: той самий датчик із тим самим часом вимірювання.
    for rec in readings:
        if (rec.get("userId") == 0
                and rec.get("userName") == sensor
                and rec.get("createdAt") == time_str):
            return None

    new_dt = _parse_dt(time_str)
    new_ts = new_dt.timestamp() if new_dt else float("-inf")

    index = len(readings)
    while index > 0:
        prev_dt = _parse_dt(readings[index - 1].get("createdAt", ""))
        prev_ts = prev_dt.timestamp() if prev_dt else float("-inf")
        if prev_ts <= new_ts:
            break
        index -= 1

    data["lastBookingId"] = data.get("lastBookingId", 0) + 1
    record = {
        "id": data["lastBookingId"],
        "userId": 0,
        "userName": sensor,
        "tableNum": 1,
        "hours": value,
        "createdAt": time_str
    }

    readings.insert(index, record)
    save_data()
    return record


def get_user_bookings(user_id: int) -> list:
    load_data()
    return [b for b in data.get("bookings", [])
            if b.get("userId") == user_id and not _is_reading(b)]


def list_bookings(include_readings: bool = False) -> list:
    load_data()
    items = data.get("bookings", [])
    if not include_readings:
        items = [b for b in items if not _is_reading(b)]
    return list(reversed(items))


def get_booking(booking_id: int):
    load_data()
    for rec in data.get("bookings", []):
        if rec.get("id") == booking_id:
            return rec
    return None


def update_booking(booking_id: int, hours: float = None, **fields):
    load_data()
    for rec in data.get("bookings", []):
        if rec.get("id") == booking_id and not _is_reading(rec):
            if hours is not None:
                rec["hours"] = float(hours)
            rec.update(fields)
            save_data()
            return rec
    return None


def delete_booking(booking_id: int, user_id: int = 0):
    """Повертає видалений запис або None (сумісно з format_booking)."""
    load_data()
    bookings = data.get("bookings", [])
    for i, b in enumerate(bookings):
        if b.get("id") == booking_id and (user_id == 0 or b.get("userId") == user_id):
            removed = bookings.pop(i)
            save_data()
            return removed
    return None


def latest_by_sensor() -> dict:
    """Останнє показання кожного датчика (без бронювань)."""
    load_data()
    latest = {}
    latest_ts = {}
    for rec in data.get("bookings", []):
        if not _is_reading(rec):
            continue
        dt = _parse_dt(rec.get("createdAt", ""))
        ts = dt.timestamp() if dt else float("-inf")
        name = rec.get("userName")
        if name not in latest_ts or ts >= latest_ts[name]:
            latest[name] = rec
            latest_ts[name] = ts
    return latest


def list_readings_last_hours(hours: float) -> list:
    """Показання за період, від найновіших до найстаріших."""
    load_data()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for rec in reversed(data.get("bookings", [])):
        if not _is_reading(rec):
            continue
        dt = _parse_dt(rec.get("createdAt", ""))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            result.append({
                "sensor": rec.get("userName"),
                "value": float(rec.get("hours", 0)),
                "createdAt": rec.get("createdAt")
            })
    return result


def list_bookings_last_hours(hours: float, now_dt: datetime = None) -> list:
    """Бронювання за останні N годин (без показань датчиків)."""
    load_data()
    now_dt = now_dt or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    cutoff = now_dt - timedelta(hours=hours)
    result = []
    for rec in reversed(data.get("bookings", [])):
        if _is_reading(rec):
            continue
        dt = _parse_dt(rec.get("createdAt", ""))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if cutoff <= dt <= now_dt:
            result.append(rec)
    return result


def list_bookings_by_day(day_text: str) -> list:
    """Бронювання за календарний день у київському часі (ДД.ММ.РРРР)."""
    load_data()
    try:
        day = datetime.strptime(day_text.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return []
    result = []
    for rec in data.get("bookings", []):
        if _is_reading(rec):
            continue
        dt = _parse_dt(rec.get("createdAt", ""))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt.astimezone(KYIV_TZ).date() == day:
            result.append(rec)
    return list(reversed(result))


def list_top_bookings(limit: int = 5) -> list:
    load_data()
    items = [b for b in data.get("bookings", []) if not _is_reading(b)]
    items.sort(key=lambda r: float(r.get("hours", 0)), reverse=True)
    return items[:max(0, int(limit))]


def add_many_bookings(user_id: int, user_name: str, items: list) -> list:
    """Пакетний імпорт: одна операція запису на весь набір."""
    load_data()
    created = []
    next_id = data.get("lastBookingId", 0)
    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        next_id += 1
        rec = {
            "id": next_id,
            "userId": user_id,
            "userName": user_name,
            "tableNum": item.get("tableNum"),
            "hours": item.get("hours"),
            "createdAt": now,
        }
        data.setdefault("bookings", []).append(rec)
        created.append(rec)
    data["lastBookingId"] = next_id
    save_data()
    return created


# --- Підписки ---
def add_subscriber(topic: str, user_id: int) -> bool:
    load_data()
    subs = data.setdefault("subscriptions", {})
    topic_list = subs.setdefault(topic, [])
    if user_id not in topic_list:
        topic_list.append(user_id)
        save_data()
        return True
    return False


def remove_subscriber(topic: str, user_id: int) -> bool:
    load_data()
    subs = data.get("subscriptions", {})
    topic_list = subs.get(topic, [])
    if user_id in topic_list:
        topic_list.remove(user_id)
        save_data()
        return True
    return False


def get_subscribers(topic: str) -> list:
    load_data()
    return data.get("subscriptions", {}).get(topic, [])


list_subscribers = get_subscribers


def is_subscribed(topic: str, user_id: int) -> bool:
    return user_id in get_subscribers(topic)


def get_user_subscriptions(user_id: int) -> list:
    load_data()
    subs = data.get("subscriptions", {})
    return [t for t, users in subs.items() if user_id in users]


# --- Нагадування ---
def add_reminder(user_id: int, text: str, remind_at: str) -> dict:
    load_data()
    data["lastReminderId"] = data.get("lastReminderId", 0) + 1
    rem = {
        "id": data["lastReminderId"],
        "userId": user_id,
        "text": text,
        "remindAt": remind_at,
        "sent": False
    }
    data.setdefault("reminders", []).append(rem)
    save_data()
    return rem


def get_user_reminders(user_id: int) -> list:
    load_data()
    return [r for r in data.get("reminders", [])
            if r.get("userId") == user_id and not r.get("sent")]


list_user_reminders = get_user_reminders


def delete_reminder(rem_id: int, user_id: int) -> bool:
    load_data()
    rems = data.get("reminders", [])
    for i, r in enumerate(rems):
        if r.get("id") == rem_id and r.get("userId") == user_id:
            rems.pop(i)
            save_data()
            return True
    return False


def remove_reminder(rem_id: int) -> bool:
    """Видалення без перевірки власника (для планувальника та /delremind)."""
    load_data()
    rems = data.get("reminders", [])
    for i, r in enumerate(rems):
        if r.get("id") == rem_id:
            rems.pop(i)
            save_data()
            return True
    return False


def get_due_reminders(now_iso: str) -> list:
    load_data()
    return [r for r in data.get("reminders", [])
            if not r.get("sent") and r.get("remindAt", "") <= now_iso]


list_due_reminders = get_due_reminders


def mark_reminder_sent(rem_id: int):
    load_data()
    for r in data.get("reminders", []):
        if r.get("id") == rem_id:
            r["sent"] = True
            save_data()
            break


# --- Щоденний звіт ---
def get_last_report_day() -> str:
    load_data()
    return data.get("lastReportDay", "")


def set_last_report_day(day_text: str):
    load_data()
    data["lastReportDay"] = day_text
    save_data()
    return day_text


# --- Етап А: 15 функцій для вебдашборда та автоматичних перевірок ---
def normalize_reading(record: dict):
    """Показання датчика в єдиному вигляді: sensor / value / createdAt / timeMs."""
    if not isinstance(record, dict) or not _is_reading(record):
        return None
    dt = _parse_dt(record.get("createdAt", ""))
    return {
        "id": record.get("id"),
        "sensor": str(record.get("userName", "")),
        "value": float(record.get("hours", 0.0)),
        "createdAt": record.get("createdAt", ""),
        "timeMs": dt.timestamp() * 1000.0 if dt else None,
    }


def list_readings(sensor: str = None, since_ms: float = None, now_ms: float = None) -> list:
    """Показання від найновіших до найстаріших із необов'язковими фільтрами."""
    load_data()
    result = []
    for rec in reversed(data.get("bookings", [])):
        norm = normalize_reading(rec)
        if norm is None or norm["timeMs"] is None:
            continue
        if sensor is not None and norm["sensor"] != sensor:
            continue
        if since_ms is not None and norm["timeMs"] < since_ms:
            continue
        if now_ms is not None and norm["timeMs"] > now_ms:
            continue
        result.append(norm)
    return result


def list_readings_by_sensor(sensor: str, hours: float = None, now_ms: float = None) -> list:
    """Показання одного датчика за період; now_ms фіксує тести."""
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    since_ms = now_ms - float(hours) * 3600 * 1000 if hours is not None else None
    return list_readings(sensor=sensor, since_ms=since_ms, now_ms=now_ms)


def get_sensor_names() -> list:
    """Відсортовані назви датчиків, які мають хоча б одне показання."""
    load_data()
    names = {
        str(rec.get("userName"))
        for rec in data.get("bookings", [])
        if _is_reading(rec) and rec.get("userName")
    }
    return sorted(names)


def count_readings(sensor: str = None, hours: float = None, now_ms: float = None) -> int:
    """Кількість показань (усіх або одного датчика) за період."""
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    since_ms = now_ms - float(hours) * 3600 * 1000 if hours is not None else None
    return len(list_readings(sensor=sensor, since_ms=since_ms, now_ms=now_ms))


def calc_sensor_stats(records: list):
    """Мін/середнє/макс для нормалізованих показань або чисел."""
    values = []
    for rec in records or []:
        raw = rec.get("value", rec.get("hours")) if isinstance(rec, dict) else rec
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return {
        "count": len(values),
        "min": min(values),
        "avg": sum(values) / len(values),
        "max": max(values),
    }


def group_by_sensor(records: list) -> dict:
    """Групування показань за назвою датчика (рядки ззовні лишаються рядками)."""
    groups = {}
    for rec in records or []:
        name = rec.get("sensor", rec.get("userName")) if isinstance(rec, dict) else None
        if name is None:
            continue
        groups.setdefault(str(name), []).append(rec)
    return groups


def summarize_sensors(hours: float = None, now_ms: float = None) -> dict:
    """Зведення count/min/avg/max для кожного датчика за період."""
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    since_ms = now_ms - float(hours) * 3600 * 1000 if hours is not None else None
    grouped = group_by_sensor(list_readings(since_ms=since_ms, now_ms=now_ms))
    return {name: calc_sensor_stats(items) for name, items in grouped.items()}


def latest_readings(limit: int = DASHBOARD_ROWS) -> list:
    """Останні N нормалізованих показань (нові зверху)."""
    return list_readings()[:max(0, int(limit))]


def chart_points(sensor: str, hours: float = None, now_ms: float = None) -> list:
    """Точки для chart.chart_to_png: від старих до нових, fields time/value."""
    items = list_readings_by_sensor(sensor, hours, now_ms)
    return [
        {"time": rec["timeMs"], "value": rec["value"]}
        for rec in reversed(items)
        if rec["timeMs"] is not None
    ]


def stale_sensors(now_ms: float = None, stale_ms: float = None) -> list:
    """Датчики, які не надсилали дані довше ніж stale_ms."""
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    stale_ms = DASHBOARD_STALE_MS if stale_ms is None else stale_ms
    result = []
    for name, rec in latest_by_sensor().items():
        dt = _parse_dt(rec.get("createdAt", ""))
        ts = dt.timestamp() * 1000.0 if dt else None
        if ts is None or now_ms - ts > stale_ms:
            result.append(name)
    return sorted(result)


def dashboard_snapshot(hours: float = None, now_ms: float = None) -> dict:
    """Усе, що потрібно /dashboard, одним знімком (без звернень до мережі)."""
    hours = DASHBOARD_PERIOD_HOURS if hours is None else hours
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    since_ms = now_ms - float(hours) * 3600 * 1000
    latest = latest_by_sensor()
    names = sorted(latest)
    grouped = group_by_sensor(list_readings(since_ms=since_ms, now_ms=now_ms))
    return {
        "nowMs": now_ms,
        "hours": hours,
        "names": names,
        "latest": latest,
        "summary": {name: calc_sensor_stats(grouped.get(name, [])) for name in names},
        "recent": list_readings(since_ms=since_ms, now_ms=now_ms)[:DASHBOARD_ROWS],
        "series": {name: chart_points(name, hours, now_ms) for name in names},
        "stale": stale_sensors(now_ms, DASHBOARD_STALE_MS),
    }


def add_test_reading(sensor: str, value: float, time_str: str) -> dict:
    """Додає показання без перевірки дубліката (для детермінованих тестів)."""
    load_data()
    dt = _parse_dt(time_str)
    ts = dt.timestamp() if dt else float("-inf")
    readings = data.setdefault("bookings", [])
    index = len(readings)
    while index > 0:
        prev_dt = _parse_dt(readings[index - 1].get("createdAt", ""))
        prev_ts = prev_dt.timestamp() if prev_dt else float("-inf")
        if prev_ts <= ts:
            break
        index -= 1
    data["lastBookingId"] = data.get("lastBookingId", 0) + 1
    record = {
        "id": data["lastBookingId"],
        "userId": 0,
        "userName": sensor,
        "tableNum": 1,
        "hours": float(value),
        "createdAt": time_str,
    }
    readings.insert(index, record)
    save_data()
    return record


def clear_readings() -> int:
    """Видаляє показання датчиків, зберігаючи звичайні бронювання."""
    load_data()
    before = len(data.get("bookings", []))
    data["bookings"] = [b for b in data.get("bookings", []) if not _is_reading(b)]
    save_data()
    return before - len(data["bookings"])


def restore_data_snapshot(snapshot: dict) -> dict:
    """Повертає стан бази зі знятого раніше make_copy() знімка."""
    save_data(copy.deepcopy(snapshot))
    return data


# Псевдоніми для сумісності з іншими модулями та тестами.
get_sensor_names_sorted = get_sensor_names
readings_by_sensor = list_readings_by_sensor
get_readings_by_sensor = list_readings_by_sensor
get_chart_points = chart_points
sensor_summary = summarize_sensors
recent_readings = latest_readings
reset_readings = clear_readings
