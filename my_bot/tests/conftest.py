"""Спільні фікстури: тестові токени, тимчасова БД та HTTP-клієнт."""

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Консоль Windows може не вміти UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEST_TOKEN = "pytest-dashboard-token-0123456789ab"
TEST_INGEST_KEY = "pytest-ingest-key-0123456789ab"
os.environ["DASHBOARD_TOKEN"] = TEST_TOKEN
os.environ["INGEST_KEY"] = TEST_INGEST_KEY
os.environ["BOT_TOKEN"] = ""

import pytest  # noqa: E402
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

import config  # noqa: E402

_TMP_DIR = tempfile.mkdtemp(prefix="pytest_smarthub_")
config.DATA_FILE = Path(_TMP_DIR) / "data.json"
config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

import storage  # noqa: E402

storage.DATA_FILE = config.DATA_FILE

import ingest  # noqa: E402


# aiohttp.web.Application прив'язується до першого event loop, у якому його
# запустили. Використовуємо один loop для всіх sync-тестів.
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_temp_dir():
    yield
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
    if not _LOOP.is_closed():
        _LOOP.close()


@pytest.fixture(autouse=True)
def clean_data():
    """Кожен тест починається з порожньої бази."""
    storage.save_data(storage._default_data())
    return storage.data


@pytest.fixture
def readings():
    """Два датчики зі свіжими показаннями + один із одним виміром."""
    now = datetime.now(timezone.utc)

    def at(minutes):
        return (now - timedelta(minutes=minutes)).isoformat()

    created = []
    for minutes, value in ((70, 34.8), (5, 35.0)):
        created.append(storage.add_test_reading("теплиця-1", value, at(minutes)))
    for minutes, value in ((80, 21.5), (4, 22.0)):
        created.append(storage.add_test_reading("теплиця-2", value, at(minutes)))
    for minutes, value in ((40, 20.0), (6, 20.2)):
        created.append(storage.add_test_reading("<b>x</b>", value, at(minutes)))
    for minutes, value in ((45, 19.8), (7, 20.1)):
        created.append(storage.add_test_reading("constructor", value, at(minutes)))
    created.append(storage.add_test_reading("одне-читання", 21.0, at(10)))
    return created


@pytest.fixture
def bookings():
    return [
        storage.add_booking(101, "Аня", 1, 3.0),
        storage.add_booking(102, "Борис", 2, 6.0),
        storage.add_booking(101, "Аня", 3, 1.5),
    ]


@pytest.fixture
def app():
    return ingest.create_app(bot=None, ingest_key=TEST_INGEST_KEY, dashboard_token=TEST_TOKEN)


def request(app, method, path, **kwargs):
    """Синхронна обгортка над aiohttp TestClient для звичайних pytest-тестів."""

    async def _run():
        async with TestClient(TestServer(app)) as client:
            response = await client.request(method, path, allow_redirects=False, **kwargs)
            body = await response.read()
            return response.status, dict(response.headers), body

    return _LOOP.run_until_complete(_run())
