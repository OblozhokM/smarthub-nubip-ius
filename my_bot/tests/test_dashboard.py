from datetime import datetime, timedelta, timezone

import config
import dashboard
import ingest
import storage

from conftest import TEST_TOKEN, request


def text_of(response):
    status, headers, body = response
    return status, headers, body.decode("utf-8")


def test_escape_html():
    assert dashboard.escape_html("<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;"
    assert dashboard.escape_html('a"b') == "a&quot;b"
    assert dashboard.escape_html(42) == "42"


def test_status_of_uses_sensor_limits():
    assert dashboard.status_of(config.SENSOR_MIN - 1)["css"] == "low"
    assert dashboard.status_of(20.0) == {"css": "ok", "text": "у нормі"}
    assert dashboard.status_of(config.SENSOR_MAX + 1)["text"] == "вище норми"


def test_time_text_is_kyiv_time():
    ms = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc).timestamp() * 1000
    assert dashboard.time_text(ms) == "12:00:00"


def test_format_ago():
    now = datetime.now(timezone.utc)
    now_ms = now.timestamp() * 1000
    assert dashboard.format_ago(now.isoformat(), now_ms) == "щойно"
    assert dashboard.format_ago((now - timedelta(minutes=5)).isoformat(), now_ms) == "5 хв тому"
    assert dashboard.format_ago((now - timedelta(hours=3)).isoformat(), now_ms) == "3 год тому"
    assert dashboard.format_ago("не дата", now_ms) == ""


def test_build_card_marks_states():
    now = datetime.now(timezone.utc)
    now_ms = now.timestamp() * 1000
    fresh = storage.add_test_reading("<b>x</b>", 35.0, now.isoformat())
    card = dashboard.build_card(fresh, now_ms)
    assert '<div class="card high">' in card
    assert "&lt;b&gt;x&lt;/b&gt;" in card
    assert "<b>x</b>" not in card

    old = storage.add_test_reading("старий", 20.0, (now - timedelta(hours=1)).isoformat())
    assert '<div class="card stale">' in dashboard.build_card(old, now_ms)


def test_build_page_empty_state():
    page = dashboard.build_page(TEST_TOKEN)
    assert "Показань ще немає" in page
    assert 'http-equiv="refresh"' in page
    assert page.endswith("</body></html>")


def test_build_page_has_all_sections_and_escapes_xss(readings):
    page = dashboard.build_page(TEST_TOKEN)
    assert "<h2>Зараз</h2>" in page
    assert "<th>Середнє</th>" in page
    assert "<h2>Останні показання</h2>" in page
    assert '<img src="/chart.png?token=' + TEST_TOKEN in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page
    assert "<b>x</b>" not in page
    assert "constructor" in page


def test_secure_headers():
    headers = dashboard.secure_headers()
    assert headers["Cache-Control"] == "no-store"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_dashboard_requires_token(app, readings):
    status, _, body = request(app, "GET", "/dashboard")
    assert status == 401
    assert "токен" in body.decode("utf-8")

    status, _, _ = request(app, "GET", "/dashboard?token=wrong")
    assert status == 401


def test_dashboard_rejects_post(app):
    status, _, _ = request(app, "POST", "/dashboard?token=" + TEST_TOKEN)
    assert status == 405


def test_dashboard_success(app, readings):
    status, headers, body = request(app, "GET", "/dashboard?token=" + TEST_TOKEN)
    page = body.decode("utf-8")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert headers["Cache-Control"] == "no-store"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "35.0" in page and "вище норми" in page


def test_dashboard_disabled_without_token(readings):
    app = ingest.create_app(dashboard_token="")
    status, _, _ = request(app, "GET", "/dashboard?token=" + TEST_TOKEN)
    assert status == 404


def test_chart_validation(app, readings):
    prefix = "/chart.png?token=" + TEST_TOKEN
    assert request(app, "GET", prefix + "&hours=6")[0] == 400
    assert request(app, "GET", prefix + "&sensor=теплиця-1&hours=abc")[0] == 400
    assert request(app, "GET", prefix + "&sensor=теплиця-1&hours=9999")[0] == 400
    assert request(app, "GET", prefix + "&sensor=одне-читання&hours=6")[0] == 404
    assert request(app, "GET", "/chart.png?sensor=теплиця-1&hours=6")[0] == 401


def test_chart_returns_png(app, readings):
    status, headers, body = request(
        app, "GET", "/chart.png?token=" + TEST_TOKEN + "&sensor=теплиця-1&hours=6"
    )
    assert status == 200
    assert headers["Content-Type"].startswith("image/png")
    assert body[:8] == b"\x89PNG\r\n\x1a\n"
    width = int.from_bytes(body[16:20], "big")
    height = int.from_bytes(body[20:24], "big")
    assert (width, height) == (640, 360)
