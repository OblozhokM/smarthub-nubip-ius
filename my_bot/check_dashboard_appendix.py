"""Скорочений лістинг check_dashboard.py: ключові перевірки дашборда.

Повний текст скрипта доступний у репозиторії проєкту.
"""
import asyncio
import os

from aiohttp import ClientSession

BASE = os.getenv("DASHBOARD_URL", "http://127.0.0.1:3000")
TOKEN = os.getenv("DASHBOARD_TOKEN", "")

results = []


def check(name, condition):
    results.append(bool(condition))
    print(f"{'OK  ' if condition else 'FAIL'} {name}")


async def fetch(session, path, method="GET"):
    async with session.request(method, BASE + path) as response:
        return response.status, dict(response.headers), await response.text()


async def main():
    if not TOKEN:
        raise SystemExit("DASHBOARD_TOKEN не задано")
    async with ClientSession() as session:
        code, _, body = await fetch(session, "/dashboard")
        check("/dashboard без токена відхилено", code == 401)
        check("тіло помилки без даних датчиків", "sensor" not in body.lower())

        code, headers, body = await fetch(session, f"/dashboard?token={TOKEN}")
        check("/dashboard з токеном доступний", code == 200)
        check("HTML містить заголовок", "<h1>" in body)
        check("Cache-Control: no-store", headers.get("Cache-Control") == "no-store")
        check("Referrer-Policy: no-referrer",
              headers.get("Referrer-Policy") == "no-referrer")
        check("X-Content-Type-Options: nosniff",
              headers.get("X-Content-Type-Options") == "nosniff")
        check("недійсний токен відхилено",
              (await fetch(session, "/dashboard?token=bad"))[0] == 401)
        check("POST на /dashboard заборонено",
              (await fetch(session, "/dashboard", "POST"))[0] == 405)

        query = f"/chart.png?token={TOKEN}&sensor=зона-1&hours=24"
        code, headers, image = await fetch(session, query)
        check("/chart.png повертає PNG", code == 200 and image.startswith("\x89PNG"))
        check("PNG не кешується", headers.get("Cache-Control") == "no-store")
        check("порожній sensor відхилено",
              (await fetch(session, f"/chart.png?token={TOKEN}&sensor=&hours=24"))[0] == 400)
        check("hours поза діапазоном відхилено",
              (await fetch(session, f"/chart.png?token={TOKEN}&sensor=зона-1&hours=100"))[0] == 400)

    passed = sum(results)
    print(f"Пройдено {passed} із {len(results)}")
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
