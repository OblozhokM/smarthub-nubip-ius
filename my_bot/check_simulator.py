import asyncio
from datetime import datetime, timezone
import httpx
from config import INGEST_KEY, INGEST_HOST, INGEST_PORT
from ingest import start_ingest_server
from utils.signal import SENSORS, generate_value, make_random

class FakeBot:
    """Заглушка бота для логування аномалій."""
    pass

async def post_test(client, url, key, body):
    headers = {"Content-Type": "application/json", "x-api-key": key}
    resp = await client.post(url, content=body, headers=headers)
    return resp.status

async def main():
    fake_bot = FakeBot()
    runner = await start_ingest_server(fake_bot)
    
    url = f"http://{INGEST_HOST}:{INGEST_PORT}/readings"
    good = '{"sensor":"зона-1","value":23.4,"time":"' + datetime.now(timezone.utc).isoformat() + '"}'
    bad_json = '{sensor:'
    bad_value = '{"sensor":"зона-1","value":"23.4","time":"' + datetime.now(timezone.utc).isoformat() + '"}'

    async with httpx.AsyncClient() as client:
        print("1) правильний запит:   ", await post_test(client, url, INGEST_KEY, good))
        print("2) неправильний ключ:  ", await post_test(client, url, "wrong-key", good))
        print("3) зламаний JSON:      ", await post_test(client, url, INGEST_KEY, bad_json))
        print("4) значення — текст:   ", await post_test(client, url, INGEST_KEY, bad_value))
        
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())