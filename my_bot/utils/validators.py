import re
import json
from datetime import datetime

def parse_number(text: str):
    if text is None:
        return None
    fixed = str(text).replace(',', '.')
    try:
        val = float(fixed)
        return val if (val == val and val != float('inf') and val != float('-inf')) else None
    except (ValueError, TypeError):
        return None

def parse_id(text: str):
    if text is None:
        return None
    try:
        val = int(text)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None

def parse_hours(text: str):
    if text is None:
        return 24.0
    val = parse_number(text)
    if val is None or val <= 0 or val > 720:
        return None
    return val

def parse_count(text: str):
    if text is None:
        return 5
    val = parse_id(text)
    if val is None or val > 20:
        return None
    return val

def parse_minutes(text: str):
    val = parse_id(text)
    if val is None or val > 10080:
        return None
    return val

def is_valid_date(date_text: str) -> bool:
    if not date_text:
        return False
    parts = date_text.strip().split('.')
    if len(parts) != 3:
        return False
    d, m, y = parts[0], parts[1], parts[2]
    if not (len(d) in (1, 2) and len(m) in (1, 2) and len(y) == 4
            and d.isdigit() and m.isdigit() and y.isdigit()):
        return False
    try:
        datetime.strptime(f"{int(d):02d}.{int(m):02d}.{y}", "%d.%m.%Y")
        return True
    except ValueError:
        return False

def parse_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^0\d{9}$", phone.strip()))

def validate_qr_code(qr: str) -> bool:
    return bool(re.match(r"^HUB-\d{2}$", qr.strip().upper()))