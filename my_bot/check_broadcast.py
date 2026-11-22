import asyncio
from broadcast import broadcast
import storage

class FakeBot:
    def __init__(self):
        self.received = []

    async def send_message(self, chat_id, text, parse_mode=None):
        if chat_id == 3:
            raise Exception("Forbidden: bot was blocked by the user")
        if chat_id == 5:
            raise Exception("Мережа недоступна")
        self.received.append(chat_id)

async def main():
    storage.load_data()
    fake_bot = FakeBot()
    
    for uid in [1, 2, 3, 4, 5]:
        storage.add_subscriber("news", uid)
        
    print("--- Запуск тестової розсилки ---")
    res = await broadcast(fake_bot, "news", "Тестова розсилка")
    
    print(f"Доставлено: {res['delivered']} | Помилок: {res['failed']}")
    print("Отримали ID:", fake_bot.received)
    print("Підписники після розсилки:", storage.list_subscribers("news"))
    
    for uid in [1, 2, 3, 4, 5]:
        storage.remove_subscriber("news", uid)

if __name__ == "__main__":
    asyncio.run(main())