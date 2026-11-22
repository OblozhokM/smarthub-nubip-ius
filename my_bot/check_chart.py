from datetime import datetime, timezone
from utils import signal, chart

sensor = signal.SENSORS[0]
rng = signal.make_random(42)
start_ms = datetime.fromisoformat("2026-11-05T08:00:00+00:00").timestamp() * 1000.0

points = [
    {"time": start_ms + step * 5 * 60 * 1000.0, "value": signal.generate_value(sensor, step, rng)}
    for step in range(72)
]

img_bytes = chart.chart_to_png(points, {"min": 10, "max": 30})
with open("chart_check.png", "wb") as f:
    f.write(img_bytes)

sig_hex = " ".join(f"{b:02x}" for b in img_bytes[:8])
w = int.from_bytes(img_bytes[16:20], "big")
h = int.from_bytes(img_bytes[20:24], "big")

print("Точок на графіку:", len(points))
print("Підпис PNG:", sig_hex)
print(f"Розмір зображення: {w}×{h} пікселів")
print("Міні-діаграма:", chart.sparkline([p["value"] for p in chart.downsample(points, 30)]))