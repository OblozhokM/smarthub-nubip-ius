"""Автоматична перевірка вебдашборда (Лабораторна 20).

Запуск: python check_dashboard.py
Скрипт не використовує реальні секрети й не змінює робочу базу даних:
токени задаються локально, а дані зберігаються у тимчасовому каталозі.
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Консоль Windows може бути в cp1251 — не даємо падати через українські рядки.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Спочатку задаємо тестові значення — config.load_dotenv() не перезапише їх.
TEST_TOKEN = "check-dashboard-token-0123456789abcdef"
TEST_INGEST_KEY = "check-ingest-key-0123456789abcdef"
os.environ["DASHBOARD_TOKEN"] = TEST_TOKEN
os.environ["INGEST_KEY"] = TEST_INGEST_KEY
os.environ.pop("BOT_TOKEN", None)

from aiohttp import ClientSession, web  # noqa: E402

import config  # noqa: E402

_TMP = tempfile.TemporaryDirectory(prefix="check_dashboard_")
_DATA_PATH = Path(_TMP.name) / "data" / "data.json"
_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
config.DATA_FILE = _DATA_PATH

import storage  # noqa: E402

storage.DATA_FILE = _DATA_PATH

import ingest  # noqa: E402

RESULTS = []


def check(name: str, condition: bool) -> None:
    RESULTS.append((name, bool(condition)))
    print(f"{'OK  ' if condition else 'FAIL'} {name}")


def seed() -> datetime:
    """Детерміновані показання відносно поточного моменту."""
    storage.clear_readings()
    now = datetime.now(timezone.utc)

    def at(minutes_ago: int) -> str:
        return (now - timedelta(minutes=minutes_ago)).isoformat()

    for minutes, value in ((70, 34.8), (5, 35.0)):
        storage.add_test_reading("теплиця-1", value, at(minutes))
    for minutes, value in ((80, 21.5), (4, 22.0)):
        storage.add_test_reading("теплиця-2", value, at(minutes))
    for minutes, value in ((40, 20.0), (6, 20.2)):
        storage.add_test_reading("<b>x</b>", value, at(minutes))
    for minutes, value in ((45, 19.8), (7, 20.1)):
        storage.add_test_reading("constructor", value, at(minutes))
    storage.add_test_reading("одне-читання", 21.0, at(10))
    return now


async def request(client: ClientSession, base: str, path: str, method: str = "GET", **kwargs):
    return await client.request(method, base + path, **kwargs)


async def main() -> int:
    seed()

    app = ingest.create_app(bot=None, ingest_key=TEST_INGEST_KEY, dashboard_token=TEST_TOKEN)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    base = f"http://127.0.0.1:{port}"

    # Другий сервер — щоб перевірити режим «токен не задано».
    off_app = ingest.create_app(bot=None, ingest_key=TEST_INGEST_KEY, dashboard_token="")
    off_runner = web.AppRunner(off_app, access_log=None)
    await off_runner.setup()
    off_site = web.TCPSite(off_runner, "127.0.0.1", 0)
    await off_site.start()
    off_port = off_runner.addresses[0][1]
    off_base = f"http://127.0.0.1:{off_port}"

    token_param = "?token=" + TEST_TOKEN
    try:
        async with ClientSession() as client:
            # --- Доступ ---
            r = await request(client, base, "/dashboard")
            check("без токена → 401", r.status == 401)
            await r.release()

            r = await request(client, base, "/dashboard?token=wrong")
            check("неправильний токен → 401", r.status == 401)
            await r.release()

            r = await request(client, base, "/chart.png?sensor=" + "теплиця-1")
            check("картинка без токена → 401", r.status == 401)
            await r.release()

            r = await request(client, base, "/dashboard" + token_param, method="POST")
            check("POST → 405", r.status == 405)
            await r.release()

            # --- Сторінка ---
            r = await request(client, base, "/dashboard" + token_param)
            html = await r.text()
            check("з токеном → 200", r.status == 200)
            check("тип text/html", r.headers.get("Content-Type", "").startswith("text/html"))
            check("Cache-Control: no-store", r.headers.get("Cache-Control") == "no-store")
            check(
                "Referrer-Policy: no-referrer",
                r.headers.get("Referrer-Policy") == "no-referrer"
                and r.headers.get("X-Content-Type-Options") == "nosniff",
            )
            check("є автооновлення", 'http-equiv="refresh"' in html)
            check(
                "картка теплиця-1 зі значенням 35.0",
                '<div class="name">теплиця-1</div><div class="value">35.0</div>' in html,
            )
            check(
                'значення 35 помічене як "вище норми"',
                '<div class="card high"><div class="name">теплиця-1</div>' in html,
            )
            check(
                'теплиця-2 "у нормі"',
                '<div class="card ok"><div class="name">теплиця-2</div>' in html,
            )
            check("є зведення (Середнє)", "<th>Середнє</th>" in html)
            check("є <img> графіка з токеном", '<img src="/chart.png?token=' + TEST_TOKEN in html)
            check(
                "назва з тегом екранована",
                "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html,
            )
            check("датчик constructor не ламає сторінку", "constructor" in html and r.status == 200)

            # --- Графік ---
            chart_path = "/chart.png?token=" + TEST_TOKEN + "&sensor=теплиця-1&hours=6"
            r = await request(client, base, chart_path)
            png = await r.read()
            check("графік → 200 image/png", r.status == 200 and r.headers.get("Content-Type", "").startswith("image/png"))
            check("підпис PNG", png[:8] == b"\x89PNG\r\n\x1a\n")

            for label, path in (
                ("hours=abc → 400", "/chart.png?token=" + TEST_TOKEN + "&sensor=теплиця-1&hours=abc"),
                ("hours=9999 → 400", "/chart.png?token=" + TEST_TOKEN + "&sensor=теплиця-1&hours=9999"),
                ("без sensor → 400", "/chart.png?token=" + TEST_TOKEN + "&hours=6"),
                ("одне показання → 404", "/chart.png?token=" + TEST_TOKEN + "&sensor=одне-читання&hours=6"),
            ):
                resp = await request(client, base, path)
                check(label, resp.status == (400 if "400" in label else 404))
                await resp.release()

            # --- Решта сервера працює як раніше ---
            now_iso = datetime.now(timezone.utc).isoformat()
            r = await request(
                client,
                base,
                "/readings",
                method="POST",
                headers={"x-api-key": TEST_INGEST_KEY},
                json={"sensor": "зона-1", "value": 23.4, "time": now_iso},
            )
            check("POST /readings → 201", r.status == 201)
            await r.release()

            r = await request(client, base, "/невідомий")
            check("невідомий шлях → 404", r.status == 404)
            await r.release()

            r = await request(client, off_base, "/dashboard" + token_param)
            check("без токена в налаштуваннях → 404", r.status == 404)
            await r.release()
    finally:
        await off_runner.cleanup()
        await runner.cleanup()

    passed = sum(ok for _, ok in RESULTS)
    failed = len(RESULTS) - passed
    print(f"\nПройдено: {passed}, помилок: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
