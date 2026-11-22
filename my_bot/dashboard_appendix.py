"""Скорочений лістинг dashboard.py: маршрутизація, захист і знімок даних.

Повний текст модуля доступний у репозиторії проєкту.
"""
import hmac
import html

import config
import storage
from utils import chart
from aiohttp import web

SECURE = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def token_ok(request) -> bool:
    expected = request.app.get("dashboard_token", config.DASHBOARD_TOKEN)
    supplied = request.query.get("token", "")
    return bool(expected) and hmac.compare_digest(str(supplied), str(expected))


def guarded(handler):
    async def wrapper(request):
        if not request.app.get("dashboard_token", config.DASHBOARD_TOKEN):
            return web.Response(text="Не знайдено", status=404, headers=SECURE)
        if request.method != "GET":
            return web.Response(text="Лише GET", status=405, headers=SECURE)
        if not token_ok(request):
            return web.Response(text="Недійсний токен", status=401, headers=SECURE)
        return await handler(request)
    return wrapper


@guarded
async def dashboard(request):
    now = storage.now_ms()
    snap = storage.dashboard_snapshot(config.DASHBOARD_PERIOD_HOURS, now)
    cards = "".join(
        f'<div class="card">{esc(r["sensor"])}: {float(r["value"]):.1f}</div>'
        for r in snap["latest"].values()
    )
    rows = "".join(
        f"<tr><td>{esc(n)}</td><td>{s['count']}</td><td>{s['avg']:.1f}</td></tr>"
        for n, s in snap["summary"].items()
    )
    body = f"<h1>Дашборд</h1><section>{cards}</section><table>{rows}</table>"
    return web.Response(text=body, content_type="text/html", headers=SECURE)


@guarded
async def chart_png(request):
    sensor = request.query.get("sensor", "")
    try:
        hours = float(request.query.get("hours", config.DASHBOARD_PERIOD_HOURS))
    except (TypeError, ValueError):
        hours = 0.0
    if not sensor or not 1 <= hours <= 72:
        return web.Response(text="sensor і hours 1..72", status=400, headers=SECURE)
    points = storage.chart_points(sensor, hours)
    if len(points) < 2:
        return web.Response(text="Недостатньо даних", status=404, headers=SECURE)
    image = chart.chart_to_png(
        chart.downsample(points, 300),
        {"min": config.SENSOR_MIN, "max": config.SENSOR_MAX},
    )
    return web.Response(body=image, content_type="image/png", headers=SECURE)


def setup_dashboard(app):
    app["dashboard_token"] = app.get("dashboard_token", config.DASHBOARD_TOKEN)
    app.router.add_get("/dashboard", dashboard)
    app.router.add_get("/chart.png", chart_png)
    return app
