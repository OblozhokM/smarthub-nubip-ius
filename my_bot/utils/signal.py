import math

SENSORS = [
    {"name": "зона-1", "base": 22.0, "amplitude": 4.0, "noise": 0.5},
    {"name": "зона-2", "base": 18.0, "amplitude": 3.0, "noise": 0.4},
]

PERIOD = 60           # тривалість однієї "доби" в тактах
ANOMALY_CHANCE = 0.03 # 3% ймовірність аномалії
ANOMALY_SIZE = 12.0   # стрибок значення при аномалії

def make_random(seed: int):
    """Лінійний конгруентний генератор псевдовипадкових чисел (LCG)."""
    state = seed
    def rng():
        nonlocal state
        state = (state * 1664525 + 1013904223) % 4294967296
        return state / 4294967296
    return rng

def generate_value(sensor: dict, step: int, random_func) -> float:
    """Генерує значення датчика з синусоїдою, шумом та можливими аномаліями."""
    wave = sensor["amplitude"] * math.sin((step / PERIOD) * 2 * math.pi)
    noise = (random_func() - 0.5) * 2 * sensor["noise"]
    val = sensor["base"] + wave + noise
    
    if random_func() < ANOMALY_CHANCE:
        direction = 1 if random_func() < 0.5 else -1
        val += direction * ANOMALY_SIZE
        
    return round(val, 1)