"""Локальний вебсервер дашборда на тестових даних (для Рисунка 3.5).

Запуск: python serve_dashboard.py
Адреса: http://127.0.0.1:8080/dashboard?token=screenshot-dashboard-token-2026
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = "screenshot-dashboard-token-2026"
os.environ["DASHBOARD_TOKEN"] = TOKEN
os.environ["INGEST_KEY"] = "screenshot-ingest-key-2026"
os.environ["BOT_TOKEN"] = ""

from aiohttp import web  # noqa: E402

import config  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="dashboard_screenshot_")
config.DATA_FILE = Path(_TMP) / "data.json"
config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

import storage  # noqa: E402
import ingest  # noqa: E402

storage.DATA_FILE = config.DATA_FILE


def seed() -> None:
    """Детерміновані показання, щоб зняти чіткий відтворюваний знімок."""
    now = datetime.now(timezone.utc)

    def at(minutes):
        return (now - timedelta(minutes=minutes)).isoformat()

    for minutes, value in ((70, 34.8), (5, 35.0)):
        storage.add_test_reading("теплиця-1", value, at(minutes))
    for minutes, value in ((80, 21.5), (4, 22.0)):
        storage.add_test_reading("теплиця-2", value, at(minutes))
    for minutes, value in ((40, 20.0), (6, 20.2)):
        storage.add_test_reading("зона-1", value, at(minutes))
    for minutes, value in ((45, 19.8), (7, 20.1)):
        storage.add_test_reading("зона-2", value, at(minutes))
    for minutes, value in ((35, 20.8), (2, 21.0)):
        storage.add_test_reading("склад", value, at(minutes))


if __name__ == "__main__":
    seed()
    app = ingest.create_app(bot=None, ingest_key=os.environ["INGEST_KEY"], dashboard_token=TOKEN)
    print(f"Дашборд: http://127.0.0.1:8080/dashboard?token={TOKEN}", flush=True)
    print("Тестові дані:", len(storage.list_readings()), "показань", flush=True)
    web.run_app(app, host="127.0.0.1", port=8080, access_log=None)
