import zlib
import struct

FONT = {
    '0': ['111', '101', '101', '101', '111'],
    '1': ['010', '110', '010', '010', '111'],
    '2': ['111', '001', '111', '100', '111'],
    '3': ['111', '001', '111', '001', '111'],
    '4': ['101', '101', '111', '001', '001'],
    '5': ['111', '100', '111', '001', '111'],
    '6': ['111', '100', '111', '101', '111'],
    '7': ['111', '001', '001', '001', '001'],
    '8': ['111', '101', '111', '101', '111'],
    '9': ['111', '101', '111', '001', '111'],
    '.': ['000', '000', '000', '000', '010'],
    '-': ['000', '000', '111', '000', '000'],
    ':': ['000', '010', '000', '010', '000'],
}

def create_canvas(width: int, height: int, background: tuple) -> dict:
    pixels = bytearray(background) * (width * height)
    return {"width": width, "height": height, "pixels": pixels}

def set_pixel(canvas: dict, x: int, y: int, color: tuple):
    if x < 0 or y < 0 or x >= canvas["width"] or y >= canvas["height"]:
        return
    idx = (y * canvas["width"] + x) * 3
    canvas["pixels"][idx:idx+3] = bytes(color)

def fill_rect(canvas: dict, x: int, y: int, w: int, h: int, color: tuple):
    for j in range(h):
        for i in range(w):
            set_pixel(canvas, x + i, y + j, color)

def draw_line(canvas: dict, x1: float, y1: float, x2: float, y2: float, color: tuple, thickness: int = 1):
    x1, y1, x2, y2 = round(x1), round(y1), round(x2), round(y2)
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    step_x = 1 if x1 < x2 else -1
    step_y = 1 if y1 < y2 else -1
    err = dx - dy
    half = thickness // 2
    while True:
        fill_rect(canvas, x1 - half, y1 - half, thickness, thickness, color)
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += step_x
        if e2 < dx:
            err += dx
            y1 += step_y

def text_width(text: str, scale: int) -> int:
    return 0 if not text else len(text) * 4 * scale - scale

def draw_text(canvas: dict, text: str, x: int, y: int, color: tuple, scale: int = 1):
    cursor = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph:
            for r in range(5):
                for c in range(3):
                    if glyph[r][c] == '1':
                        fill_rect(canvas, cursor + c * scale, y + r * scale, scale, scale, color)
        cursor += 4 * scale

def _make_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xffffffff
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

def encode_png(canvas: dict) -> bytes:
    w, h = canvas["width"], canvas["height"]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    row_size = w * 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(canvas["pixels"][y * row_size : (y + 1) * row_size])
    signature = b"\x89PNG\r\n\x1a\n"
    return (
        signature
        + _make_chunk(b"IHDR", ihdr)
        + _make_chunk(b"IDAT", zlib.compress(bytes(raw)))
        + _make_chunk(b"IEND", b"")
    )