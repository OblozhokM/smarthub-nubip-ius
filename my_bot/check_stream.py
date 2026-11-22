import asyncio
from datetime import datetime, timezone, timedelta
import httpx
from ingest import start_ingest_server
from utils import outbox

from config import INGEST_KEY, INGEST_PORT

class FakeBot:
    async def send_message(self, *args, **kwargs):
        pass

network_up = False
lose_responses = 0
url = ""

async def send_mock(reading):
    global lose_responses
    if not network_up:
        raise Exception("fetch failed")
        
    headers = {"Content-Type": "application/json", "x-api-key": INGEST_KEY}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=reading, headers=headers)
        
    if lose_responses > 0:
        lose_responses -= 1
        raise Exception("timeout")
        
    if resp.status_code not in (200, 201):
        err = Exception(f"Бот відповів помилкою {resp.status_code}")
        setattr(err, "status", resp.status_code)
        raise err
    return resp.json()

def create_reading(sensor, value, offset_sec):
    t = datetime.now(timezone.utc) - timedelta(seconds=offset_sec)
    return {"sensor": sensor, "value": value, "time": t.isoformat()}

async def main():
    global network_up, lose_responses, url
    fake_bot = FakeBot()
    test_port = 3005
    runner = await start_ingest_server(fake_bot, port=test_port)
    url = f"http://127.0.0.1:{test_port}/readings"
    
    queue = []
    outbox.add_to_queue(queue, create_reading("зона-1", 20, 50), 10)
    outbox.add_to_queue(queue, create_reading("зона-2", 18, 49), 10)
    
    print("1) Мережі немає:        ", await outbox.flushQueue(queue, send_mock))
    network_up = True
    print("2) Мережа з'явилась:    ", await outbox.flushQueue(queue, send_mock))
    
    # Втрата відповіді та дублікат
    outbox.add_to_queue(queue, create_reading("зона-1", 22, 30), 10)
    lose_responses = 1
    print("3) Відповідь загубилась:", await outbox.flushQueue(queue, send_mock))
    print("   Повторна відправка:  ", await outbox.flushQueue(queue, send_mock))
    
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())