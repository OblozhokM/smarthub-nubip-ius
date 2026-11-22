from datetime import datetime, timezone, timedelta
import storage
from utils import signal

rng = signal.make_random(42)
now = datetime.now(timezone.utc)

for step in range(72):
    t_str = (now - timedelta(minutes=(71 - step) * 5)).isoformat()
    for sensor in signal.SENSORS:
        val = signal.generate_value(sensor, step, rng)
        storage.add_device_reading(sensor["name"], val, t_str)

print("Додано показань: 144 (2 датчики × 72 кроки по 5 хвилин).")