import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram-бота з .env (не хардкодити у коді).
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "data.json"
IMPORT_FILE = BASE_DIR / "import" / "bookings.csv"
REPORT_TIME = "08:00"

TOPICS = {
    "report": "Щоденні звіти",
    "alert": "Критичні події системи",
    "news": "Новини та оновлення"
}

# --- Межі для бронювань (години) ---
BOOKING_MIN = 0.5
BOOKING_MAX = 8.0

# Діапазон значень індикатора: той самий, що і для бронювань.
ALERT_MIN = BOOKING_MIN
ALERT_MAX = BOOKING_MAX

# --- Межі для показників датчиків (температура, °C) ---
SENSOR_MIN = 15.0
SENSOR_MAX = 28.0

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BROADCAST_PAUSE_MS = 50

# --- Лабораторна ЛР-16: API погоди ---
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_CITY = "Київ"
HTTP_TIMEOUT_SECONDS = 5.0
WEATHER_CACHE_SECONDS = 10 * 60

# --- Лабораторна ЛР-17: отримання даних від датчиків (Ingest & Simulator) ---
INGEST_KEY = os.getenv("INGEST_KEY", "")
INGEST_PORT = int(os.getenv("INGEST_PORT", "3000"))
INGEST_HOST = os.getenv("INGEST_HOST", "127.0.0.1")
INGEST_URL = f"http://{INGEST_HOST}:{INGEST_PORT}/readings"

# --- Лабораторна ЛР-20: вебдашборд ---
DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_PERIOD_HOURS = 6
DASHBOARD_ROWS = 10
DASHBOARD_STALE_MS = 10 * 60 * 1000
DASHBOARD_REFRESH_SECONDS = 30
