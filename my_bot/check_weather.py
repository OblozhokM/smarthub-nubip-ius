import asyncio
import weather

async def main():
    print("--- 1. Початковий запит погоди у Києві ---")
    w1 = await weather.weather_for_city("Київ")
    print("Результат 1:", w1)
    
    print("\n--- 2. Повторний запит (має взятися з КЕШУ) ---")
    w2 = await weather.weather_for_city("київ")
    print("Результат 2:", w2)
    
    print("\n--- 3. Запит для невідомого міста ---")
    w3 = await weather.weather_for_city("НевідомеМісто123")
    print("Результат 3 (має бути None):", w3)

if __name__ == "__main__":
    asyncio.run(main())