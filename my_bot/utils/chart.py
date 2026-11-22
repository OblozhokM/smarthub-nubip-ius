import math
from datetime import datetime, timezone, timedelta
from utils import png

BLOCKS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

WHITE = (255, 255, 255)
GRAY = (225, 225, 225)
DARK = (60, 60, 60)
BLUE = (28, 114, 147)
GREEN = (46, 160, 90)
RED = (200, 60, 60)
AMBER = (242, 166, 90)

def sparkline(values: list) -> str:
    if not values:
        return ""
    v_min, v_max = min(values), max(values)
    out = []
    for v in values:
        level = 3 if v_max == v_min else round((v - v_min) / (v_max - v_min) * 7)
        out.append(BLOCKS[level])
    return "".join(out)

def downsample(points: list, max_points: int) -> list:
    if len(points) <= max_points:
        return points
    size = math.ceil(len(points) / max_points)
    result = []
    for start in range(0, len(points), size):
        chunk = points[start : start + size]
        avg_t = sum(p["time"] for p in chunk) / len(chunk)
        avg_v = sum(p["value"] for p in chunk) / len(chunk)
        result.append({"time": avg_t, "value": avg_v})
    return result

def _clock_kyiv(timestamp_ms: float) -> str:
    kyiv_tz = timezone(timedelta(hours=2))
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=kyiv_tz)
    return dt.strftime("%H:%M")

def make_view(points: list, plot: dict) -> dict:
    t_min = points[0]["time"]
    t_max = points[-1]["time"]
    v_min = min(p["value"] for p in points)
    v_max = max(p["value"] for p in points)
    padding = (v_max - v_min) * 0.05
    if padding == 0:
        padding = 1.0
    return {
        "tMin": t_min,
        "tMax": t_max,
        "vMin": v_min - padding,
        "vMax": v_max + padding,
        "left": plot["left"],
        "top": plot["top"],
        "width": plot["width"],
        "height": plot["height"],
    }

def to_x(view: dict, time_ms: float) -> int:
    if view["tMax"] == view["tMin"]:
        return view["left"]
    return round(view["left"] + (time_ms - view["tMin"]) / (view["tMax"] - view["tMin"]) * view["width"])

def to_y(view: dict, value: float) -> int:
    return round(view["top"] + view["height"] - (value - view["vMin"]) / (view["vMax"] - view["vMin"]) * view["height"])

def build_line_chart(points: list, limits: dict) -> dict:
    width, height = 640, 360
    canvas = png.create_canvas(width, height, WHITE)
    view = make_view(points, {"left": 70, "top": 20, "width": width - 90, "height": height - 65})
    bottom = view["top"] + view["height"]
    right = view["left"] + view["width"]

    # Сітка та підписи осі Y
    for i in range(5):
        val = view["vMin"] + (view["vMax"] - view["vMin"]) * i / 4
        y = to_y(view, val)
        png.draw_line(canvas, view["left"], y, right, y, GRAY, 1)
        label = f"{val:.1f}"
        png.draw_text(canvas, label, view["left"] - 8 - png.text_width(label, 2), y - 5, DARK, 2)

    # Пунктирні лінії меж норми
    for lim in (limits.get("min"), limits.get("max")):
        if lim is not None and view["vMin"] < lim < view["vMax"]:
            y = to_y(view, lim)
            for x in range(view["left"], right, 14):
                png.draw_line(canvas, x, y, min(x + 7, right), y, AMBER, 2)

    # Осі X та Y
    png.draw_line(canvas, view["left"], view["top"], view["left"], bottom, DARK, 2)
    png.draw_line(canvas, view["left"], bottom, right, bottom, DARK, 2)

    # Підписи часу на осі X
    s_lbl = _clock_kyiv(view["tMin"])
    m_lbl = _clock_kyiv((view["tMin"] + view["tMax"]) / 2)
    e_lbl = _clock_kyiv(view["tMax"])
    png.draw_text(canvas, s_lbl, view["left"], bottom + 12, DARK, 2)
    png.draw_text(canvas, m_lbl, round((view["left"] + right) / 2 - png.text_width(m_lbl, 2) / 2), bottom + 12, DARK, 2)
    png.draw_text(canvas, e_lbl, right - png.text_width(e_lbl, 2), bottom + 12, DARK, 2)

    # Лінія тренду
    for i in range(1, len(points)):
        png.draw_line(
            canvas,
            to_x(view, points[i - 1]["time"]),
            to_y(view, points[i - 1]["value"]),
            to_x(view, points[i]["time"]),
            to_y(view, points[i]["value"]),
            BLUE,
            2,
        )

    # Точки (якщо їх <= 60)
    if len(points) <= 60:
        for p in points:
            png.fill_rect(canvas, to_x(view, p["time"]) - 2, to_y(view, p["value"]) - 2, 5, 5, BLUE)

    # Маркери мінімуму (зелений) та максимуму (червоний)
    min_pt = min(points, key=lambda p: p["value"])
    max_pt = max(points, key=lambda p: p["value"])
    png.fill_rect(canvas, to_x(view, min_pt["time"]) - 4, to_y(view, min_pt["value"]) - 4, 9, 9, GREEN)
    png.fill_rect(canvas, to_x(view, max_pt["time"]) - 4, to_y(view, max_pt["value"]) - 4, 9, 9, RED)

    return canvas

def chart_to_png(points: list, limits: dict) -> bytes:
    return png.encode_png(build_line_chart(points, limits))