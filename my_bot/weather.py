import time
import logging
import urllib.parse
import httpx
from config import (
    GEOCODING_URL,
    FORECAST_URL,
    DEFAULT_CITY,
    HTTP_TIMEOUT_SECONDS,
    WEATHER_CACHE_SECONDS
)

# Кеш у пам'яті: { city_lower: {"savedAt": timestamp, "weather": dict} }
cache = {}

async def get_json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise ValueError(f"Сервіс відповів помилкою {response.status_code}")
        try:
            return response.json()
        except Exception:
            raise ValueError("Відповідь сервісу не є JSON")

async def find_city(name: str):
    encoded_name = urllib.parse.quote(name.strip())
    url = f"{GEOCODING_URL}?name={encoded_name}&count=1&language=uk"
    data = await get_json(url)
    
    results = data.get("results")
    if not results or len(results) == 0:
        return None
        
    city = results[0]
    return {
        "name": city.get("name"),
        "latitude": city.get("latitude"),
        "longitude": city.get("longitude")
    }

async def get_current_weather(latitude: float, longitude: float):
    url = (
        f"{FORECAST_URL}?latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
    )
    data = await get_json(url)
    current = data.get("current")
    
    if not current or "temperature_2m" not in current:
        raise ValueError("Несподівана відповідь сервісу: немає температури")
        
    return {
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind": current.get("wind_speed_10m")
    }

async def weather_for_city(name: str):
    key = name.strip().lower()
    now = time.time()
    
    # 1. Перевірка кешу
    if key in cache:
        saved = cache[key]
        if now - saved["savedAt"] < WEATHER_CACHE_SECONDS:
            logging.info(f"❄️ Отримано погоду для '{name}' з КЕШУ")
            return saved["weather"]
            
    # 2. Запит до API
    city = await find_city(name)
    if city is None:
        return None
        
    current = await get_current_weather(city["latitude"], city["longitude"])
    weather = {
        "city": city["name"],
        "temperature": current["temperature"],
        "humidity": current["humidity"],
        "wind": current["wind"]
    }
    
    # Збереження в кеш
    cache[key] = {
        "savedAt": now,
        "weather": weather
    }
    return weather

def clear_cache():
    cache.clear()