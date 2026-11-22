"""Мінімальний вебдашборд: /dashboard і /chart.png на тому ж HTTP-сервері.

Доступ захищено токеном DASHBOARD_TOKEN. Усі дані, що надходять ззовні
(назви датчиків), екрануються перед вставкою в HTML — захист від XSS.
"""

import hmac
import html
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from aiohttp import web

import config
import storage
from utils import chart

PERIOD_HOURS = config.DASHBOARD_PERIOD_HOURS
STALE_MS = config.DASHBOARD_STALE_MS
TABLE_ROWS = config.DASHBOARD_ROWS
REFRESH_SECONDS = config.DASHBOARD_REFRESH_SECONDS

KYIV_TZ = timezone(timedelta(hours=2))


def escape_html(text) -> str:
    """Робить довільний рядок безпечним для вставки в HTML."""
    return html.escape(str(text), quote=True)


def status_of(value: float) -> dict:
    """Стан температури відносно меж норми для датчиків."""
    value = float(value)
    if value < config.SENSOR_MIN:
        return {"css": "low", "text": "нижче норми"}
    if value > config.SENSOR_MAX:
        return {"css": "high", "text": "вище норми"}
    return {"css": "ok", "text": "у нормі"}


def time_text(ms: float) -> str:
    """Час за Києвом у форматі HH:MM:SS."""
    dt = datetime.fromtimestamp(float(ms) / 1000.0, tz=KYIV_TZ)
    return dt.strftime("%H:%M:%S")


def format_ago(iso_str: str, now_ms: float) -> str:
    """Людський вигляд різниці між часом показання й поточним моментом."""
    try:
        raw = str(iso_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff_sec = max(0, int(now_ms / 1000.0 - dt.timestamp()))
        if diff_sec < 60:
            return "щойно"
        if diff_sec < 3600:
            return f"{diff_sec // 60} хв тому"
        return f"{diff_sec // 3600} год тому"
    except Exception:
        return ""


def build_card(record: dict, now_ms: float) -> str:
    """Картка одного датчика: значення, стан і час останнього показання."""
    norm = storage.normalize_reading(record) or {}
    value = float(norm.get("value", 0.0))
    status = status_of(value)
    css, note = status["css"], status["text"]

    time_ms = norm.get("timeMs")
    if time_ms is None or now_ms - time_ms > STALE_MS:
        css, note = "stale", "немає свіжих даних"

    sensor_name = escape_html(norm.get("sensor", ""))
    ago = escape_html(format_ago(norm.get("createdAt", ""), now_ms))
    return (
        f'<div class="card {css}">'
        f'<div class="name">{sensor_name}</div>'
        f'<div class="value">{value:.1f}</div>'
        f'<div class="note">{escape_html(note)} · {ago}</div>'
        "</div>"
    )


_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px; background: #fff; color: #1f2933;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 18px; line-height: 1.45;
}
h1 { margin: 0 0 6px; font-size: 30px; }
h2 { margin: 30px 0 12px; font-size: 22px; }
.small { color: #617080; font-size: 15px; }
.cards { display: flex; flex-wrap: wrap; gap: 14px; }
.card {
  flex: 1 1 190px; max-width: 260px; padding: 16px 18px; border-radius: 12px;
  border: 1px solid #d9e2ec; background: #f8fafc;
}
.card.ok { border-color: #2ba55c; background: #f0fbf4; }
.card.low { border-color: #2f78c7; background: #f0f7ff; }
.card.high { border-color: #d64545; background: #fff2f2; }
.card.stale { border-color: #9aa5b1; background: #f3f4f6; color: #6b7280; }
.name { font-weight: 700; word-break: break-word; }
.value { font-size: 36px; font-weight: 700; line-height: 1.1; margin: 6px 0; }
.note { font-size: 14px; color: #52606d; }
table { border-collapse: collapse; width: 100%; max-width: 900px; background: #fff; }
th, td { border: 1px solid #d9e2ec; padding: 8px 12px; text-align: left; }
th { background: #f0f4f8; }
img { max-width: 100%; height: auto; border: 1px solid #d9e2ec; border-radius: 8px; }
code { background: #f0f4f8; padding: 2px 6px; border-radius: 4px; }
@media (max-width: 600px) { body { padding: 16px; font-size: 16px; } .cards { flex-direction: column; } }
"""


def build_page(token: str, now_ms: float = None) -> str:
    """Генерує всю HTML-сторінку лише з даних storage (без мережі)."""
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0
    snapshot = storage.dashboard_snapshot(PERIOD_HOURS, now_ms)
    names = snapshot["names"]

    page = (
        "<!DOCTYPE html><html lang=\"uk\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta http-equiv="refresh" content="{REFRESH_SECONDS}">'
        "<title>Дашборд датчиків</title>"
        f"<style>{_STYLE}</style></head><body>"
    )
    page += (
        "<h1>Дашборд датчиків</h1>"
        f'<div class="small">Оновлено о {time_text(now_ms)} · сторінка оновлюється кожні '
        f"{REFRESH_SECONDS} с · норма: від {config.SENSOR_MIN:g} до {config.SENSOR_MAX:g} °C</div>"
    )

    if not names:
        return (
            page + "<p>Показань ще немає. Запустіть симулятор: "
            "<code>python simulator.py 2</code></p></body></html>"
        )

    # 1. Картки поточних показань
    page += "<h2>Зараз</h2><div class=\"cards\">"
    for name in names:
        page += build_card(snapshot["latest"][name], now_ms)
    page += "</div>"

    # 2. Зведення за період
    page += (
        f"<h2>Зведення за {PERIOD_HOURS} год</h2>"
        "<table><tr><th>Датчик</th><th>Показань</th><th>Мін</th>"
        "<th>Середнє</th><th>Макс</th></tr>"
    )
    for name in names:
        stats = snapshot["summary"].get(name)
        safe_name = escape_html(name)
        if not stats:
            page += f"<tr><td>{safe_name}</td><td colspan=\"4\">немає даних</td></tr>"
        else:
            page += (
                f"<tr><td>{safe_name}</td><td>{stats['count']}</td>"
                f"<td>{stats['min']:.1f}</td><td>{stats['avg']:.1f}</td>"
                f"<td>{stats['max']:.1f}</td></tr>"
            )
    page += "</table>"

    # 3. Графіки: браузер окремим запитом звертається до /chart.png
    page += f"<h2>Графіки за {PERIOD_HOURS} год</h2>"
    for name in names:
        src = (
            "/chart.png?token=" + quote(str(token), safe="")
            + "&sensor=" + quote(name, safe="")
            + f"&hours={PERIOD_HOURS}"
        )
        safe_name = escape_html(name)
        page += (
            f"<div><b>{safe_name}</b><br>"
            f'<img src="{escape_html(src)}" alt="графік {safe_name}"></div>'
        )

    # 4. Останні показання
    page += (
        "<h2>Останні показання</h2>"
        "<table><tr><th>Час</th><th>Датчик</th><th>Значення</th></tr>"
    )
    for rec in snapshot["recent"][:TABLE_ROWS]:
        when = time_text(rec["timeMs"]) if rec.get("timeMs") is not None else ""
        page += (
            f"<tr><td>{when}</td><td>{escape_html(rec['sensor'])}</td>"
            f"<td>{float(rec['value']):.1f}</td></tr>"
        )
    page += "</table></body></html>"
    return page


def secure_headers() -> dict:
    """Заголовки, що забороняють кешування й розкриття адреси з токеном."""
    return {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


def text_response(text: str, status: int = 200, content_type: str = "text/plain") -> web.Response:
    return web.Response(text=text, status=status, content_type=content_type, headers=secure_headers())


def _token_ok(request: web.Request) -> bool:
    expected = request.app.get("dashboard_token", config.DASHBOARD_TOKEN)
    supplied = request.query.get("token", "")
    return bool(expected) and hmac.compare_digest(str(supplied), str(expected))


def _unauthorized() -> web.Response:
    return text_response("Потрібен правильний токен: /dashboard?token=...", 401)


async def dashboard_handler(request: web.Request) -> web.Response:
    # Порядок перевірок: увімкнено → метод → токен → дані.
    if not request.app.get("dashboard_token", config.DASHBOARD_TOKEN):
        return text_response("Не знайдено", 404)
    if request.method != "GET":
        return text_response("Використовуйте GET", 405)
    if not _token_ok(request):
        return _unauthorized()
    return text_response(build_page(request.app["dashboard_token"]), 200, "text/html")


async def chart_handler(request: web.Request) -> web.Response:
    if not request.app.get("dashboard_token", config.DASHBOARD_TOKEN):
        return text_response("Не знайдено", 404)
    if request.method != "GET":
        return text_response("Використовуйте GET", 405)
    if not _token_ok(request):
        return _unauthorized()

    sensor = request.query.get("sensor", "")
    raw_hours = request.query.get("hours", str(PERIOD_HOURS))
    try:
        hours = float(raw_hours)
    except (TypeError, ValueError):
        hours = float("nan")
    if not sensor or not (1 <= hours <= 72):
        return text_response("Потрібні sensor і hours (від 1 до 72)", 400)

    points = storage.chart_points(sensor, hours)
    if len(points) < 2:
        return text_response("Для графіка потрібно щонайменше 2 показання", 404)

    limits = {"min": config.SENSOR_MIN, "max": config.SENSOR_MAX}
    image = chart.chart_to_png(chart.downsample(points, 300), limits)
    return web.Response(body=image, content_type="image/png", headers=secure_headers())


def setup_dashboard(app: web.Application) -> web.Application:
    """Підключає маршрути дашборда до вже наявного HTTP-застосунку."""
    app["dashboard_token"] = app.get("dashboard_token", config.DASHBOARD_TOKEN)
    app.router.add_route("*", "/dashboard", dashboard_handler)
    app.router.add_route("*", "/chart.png", chart_handler)
    return app
