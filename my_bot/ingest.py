import logging
from datetime import datetime, timezone
from aiohttp import web
from config import INGEST_KEY, INGEST_HOST, INGEST_PORT, DASHBOARD_TOKEN
import storage
from alerts import check_reading
import dashboard

MAX_BODY_SIZE = 10 * 1024
MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000   # 7 діб
MAX_FUTURE_MS = 5 * 60 * 1000          # 5 хвилин
ALERT_RECENT_MS = 10 * 60 * 1000       # Сповіщення лише для свіжих показань (< 10 хв)


def is_valid_time(time_str: str) -> bool:
    if not isinstance(time_str, str):
        return False
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return False
        now = datetime.now(timezone.utc)
        diff_ms = (now - dt).total_seconds() * 1000
        return -MAX_FUTURE_MS <= diff_ms <= MAX_AGE_MS
    except Exception:
        return False


async def handle_readings(request: web.Request):
    bot = request.app.get("bot")
    expected_key = request.app.get("ingest_key", INGEST_KEY)

    api_key = request.headers.get("x-api-key")
    if not expected_key or api_key != expected_key:
        return web.json_response({"ok": False, "error": "wrong key"}, status=401)

    if request.content_length and request.content_length > MAX_BODY_SIZE:
        return web.json_response({"ok": False, "error": "body too large"}, status=413)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    if not isinstance(data, dict):
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    sensor = data.get("sensor")
    value = data.get("value")
    time_str = data.get("time")

    if not isinstance(sensor, str) or not sensor or len(sensor) > 30:
        return web.json_response({"ok": False, "error": "invalid sensor"}, status=400)

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return web.json_response({"ok": False, "error": "invalid value"}, status=400)

    if not is_valid_time(time_str):
        return web.json_response({"ok": False, "error": "invalid time"}, status=400)

    try:
        record = storage.add_device_reading(sensor, float(value), time_str)
    except Exception as e:
        logging.error(f"Ingest save error: {e}")
        return web.json_response({"ok": False, "error": "save failed"}, status=500)

    if record is None:
        return web.json_response({"ok": True, "duplicate": True}, status=200)

    # Перевірка на аномалію лише якщо показання свіже
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - dt).total_seconds() * 1000 < ALERT_RECENT_MS:
            if bot:
                check_reading(bot, record)
    except Exception:
        pass

    return web.json_response({"ok": True, "id": record["id"]}, status=201)


def create_app(bot=None, ingest_key: str = None, dashboard_token: str = None) -> web.Application:
    """Фабрика застосунку: /readings + /dashboard + /chart.png (ЛР17–ЛР20)."""
    app = web.Application(client_max_size=MAX_BODY_SIZE)
    app["bot"] = bot
    app["ingest_key"] = INGEST_KEY if ingest_key is None else ingest_key
    # Явний аргумент перевірки потрібен тестам; у звичайному запуску беремо
    # токен із конфігурації, інакше дашборд завжди був би «вимкненим».
    app["dashboard_token"] = DASHBOARD_TOKEN if dashboard_token is None else dashboard_token
    app.router.add_post("/readings", handle_readings)
    dashboard.setup_dashboard(app)
    return app


async def start_ingest_server(bot=None, host=None, port=None, dashboard_token=None):
    if not INGEST_KEY:
        logging.warning("⚠️ INGEST_KEY не вказано в .env: приймання вимкнено.")
        return None

    use_host = host or INGEST_HOST
    use_port = port if port is not None else INGEST_PORT
    app = create_app(bot, dashboard_token=dashboard_token)

    # access_log=None: токен дашборда не потрапляє в журнал запитів.
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, use_host, use_port)
    await site.start()

    print(f"📡 Приймання показань: http://{use_host}:{use_port}/readings")
    print(f"🖥  Дашборд:          http://{use_host}:{use_port}/dashboard?token=***")
    return runner
