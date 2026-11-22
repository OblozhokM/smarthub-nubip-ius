from pathlib import Path
from utils.validators import parse_number, parse_id

def read_csv_file(file_path: Path):
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except Exception as e:
        raise e

def parse_csv(text: str):
    lines = text.splitlines()
    if not lines:
        return []

    # Визначаємо розділювач по першому рядку
    separator = ";" if ";" in lines[0] else ","
    rows = []
    
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        cells = [cell.strip() for cell in line_clean.split(separator)]
        rows.append({"lineNumber": idx + 1, "cells": cells})
        
    return rows

def bookings_from_csv(text: str):
    rows = parse_csv(text)
    good = []
    errors = []

    # Пропускаємо перший рядок (заголовок)
    for row in rows[1:]:
        line_num = row["lineNumber"]
        cells = row["cells"]

        if len(cells) < 2:
            errors.append(f"Рядок {line_num}: має бути два стовпці (стіл і години)")
            continue

        table_num = parse_id(cells[0])
        hours = parse_number(cells[1])

        if table_num is None or not (1 <= table_num <= 10):
            errors.append(f"Рядок {line_num}: некоректний номер столу «{cells[0]}» (має бути від 1 до 10)")
            continue

        if hours is None or not (0.5 <= hours <= 24.0):
            errors.append(f"Рядок {line_num}: некоректні години «{cells[1]}»")
            continue

        good.append({"tableNum": table_num, "hours": hours})

    return {"good": good, "errors": errors}