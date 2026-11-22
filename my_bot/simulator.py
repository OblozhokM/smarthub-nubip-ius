import asyncio
import sys
from datetime import datetime, timezone

import httpx

from config import HTTP_TIMEOUT_SECONDS, INGEST_KEY, INGEST_URL
from utils.outbox import add_to_queue, flush_queue
from utils.signal import SENSORS, generate_value, make_random

MAX_QUEUE = 100


async def send_reading(client: httpx.AsyncClient, reading: dict):
    headers = {"Content-Type": "application/json", "x-api-key": INGEST_KEY}
    resp = await client.post(
        INGEST_URL, json=reading, headers=headers, timeout=HTTP_TIMEOUT_SECONDS
    )
    if resp.status_code not in (200, 201):
        err = ValueError(f"Неочікуваний статус відповіді {resp.status_code}")
        setattr(err, "status", resp.status_code)
        raise err
    return resp.json()


async def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    import random as sys_random

    rng = make_random(seed) if seed != 0 else sys_random.random

    queue = []
    step = 0
    print(f"Симулятор запущено: інтервал {interval} с. Зупинка — Ctrl+C.")

    async with httpx.AsyncClient() as client:
        while ticks == 0 or step < ticks:
            values = []
            lost = 0
            for sensor in SENSORS:
                val = generate_value(sensor, step, rng)
                values.append(f"{sensor['name']} {val}")
                reading = {
                    "sensor": sensor["name"],
                    "value": val,
                    "time": datetime.now(timezone.utc).isoformat(),
                }
                lost += add_to_queue(queue, reading, MAX_QUEUE)

            if lost > 0:
                print(f"Увага: черга переповнена, відкинуто {lost} показників.")

            async def _send(r):
                return await send_reading(client, r)

            res = await flush_queue(queue, _send)
            text = (
                f"#{step} {', '.join(values)} -> відправлено {res['sent']}, "
                f"у черзі {res['left']}"
            )
            if res["dropped"] > 0:
                text += f", відкинуто {res['dropped']}"
            if res["error"]:
                text += f" ({res['error']})"
            print(text)

            step += 1
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
