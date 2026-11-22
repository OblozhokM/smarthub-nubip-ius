from datetime import datetime, timezone, timedelta
from utils.stats import group_by_table, calc_stats

NOT_FOUND_TEXT = "⚠️ Запису про бронювання з таким номером не знайдено."
SAVE_FAILED_TEXT = "❌ Не вдалося зберегти зміни. Спробуйте пізніше."

def format_booking(record: dict) -> str:
    try:
        raw = str(record.get("createdAt", "")).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        kyiv_tz = timezone(timedelta(hours=2))
        dt_kyiv = dt.astimezone(kyiv_tz)
        when = dt_kyiv.strftime("%d.%m.%Y, %H:%M:%S")
    except Exception:
        when = record.get("createdAt", "")
        
    return f"📌 **Бронь #{record.get('id')}** | Стіл №{record.get('tableNum')} | {record.get('hours')} год. | 👤 {record.get('userName')} | 🕒 {when}"

def format_reminder(reminder: dict) -> str:
    raw = reminder.get("remindAt") or reminder.get("dueAt") or ""
    try:
        dt = datetime.fromisoformat(raw)
        kyiv_tz = timezone(timedelta(hours=2))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_kyiv = dt.astimezone(kyiv_tz)
        when = dt_kyiv.strftime("%d.%m.%Y %H:%M")
    except Exception:
        when = raw
    return f"⏰ **#{reminder.get('id')}** · {when} · {reminder.get('text')}"

def format_weather(w: dict) -> str:
    return f"🌤 **Погода у м. {w['city']}:**\n• Температура: `{w['temperature']} °C`\n• Вологість: `{w['humidity']} %`\n• Вітер: `{w['wind']} км/год`"

def format_ago(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return "щойно"
        if minutes < 60:
            return f"{minutes} хв тому"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} год тому"
        days = hours // 24
        return f"{days} дн тому"
    except Exception:
        return ""

def format_period_report(title: str, items: list) -> str:
    if not items:
        return f"📋 **{title}:** записів немає."
    text = f"📋 **{title}:** знайдено {len(items)} запис(ів)\n"
    limit = 10
    for rec in items[:limit]:
        ago = format_ago(rec.get("createdAt"))
        ago_text = f" ({ago})" if ago else ""
        text += f"\n{format_booking(rec)}{ago_text}"
    if len(items) > limit:
        text += f"\n… і ще {len(items) - limit}"
    return text

def format_stats_report(title: str, records: list) -> str:
    if not records:
        return f"📊 **{title}:** записів немає."
    
    groups = group_by_table(records)
    text = f"📊 **{title}:** {len(records)} запис(ів)\n"
    
    shown = 0
    hidden = 0
    for table_name, recs in groups.items():
        if shown >= 10:
            hidden += 1
            continue
        s = calc_stats(recs)
        text += f"\n• **{table_name}**: {s['count']} шт | мін: {s['min']}г | макс: {s['max']}г | сер: {s['avg']:.1f}г"
        shown += 1
        
    if hidden > 0:
        text += f"\n… і ще столів: {hidden}"
        
    return text

def format_import_report(added_count: int, errors: list) -> str:
    text = f"✅ **Імпортовано записів:** {added_count}"
    if errors:
        text += f"\n⚠️ **Пропущено рядків:** {len(errors)}"
        limit = 5
        for err in errors[:limit]:
            text += f"\n• {err}"
        if len(errors) > limit:
            text += f"\n… і ще {len(errors) - limit}"
    return text