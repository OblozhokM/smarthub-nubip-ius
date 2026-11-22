from datetime import datetime, timezone, timedelta
from pathlib import Path
import storage
from config import DATA_FILE

if DATA_FILE.exists():
    DATA_FILE.unlink()

storage.load_data()

def hours_ago(hours: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.isoformat()

test_items = [
    {"tableNum": 1, "hours": 2.0, "createdAt": hours_ago(72)},
    {"tableNum": 2, "hours": 1.5, "createdAt": hours_ago(50)},
    {"tableNum": 1, "hours": 2.5, "createdAt": hours_ago(25)},
    {"tableNum": 1, "hours": 3.0, "createdAt": hours_ago(20)},
    {"tableNum": 2, "hours": 4.0, "createdAt": hours_ago(12)},
    {"tableNum": 1, "hours": 6.0, "createdAt": hours_ago(5)},
    {"tableNum": 2, "hours": 2.0, "createdAt": hours_ago(3)},
    {"tableNum": 1, "hours": 5.0, "createdAt": hours_ago(1)},
]

copy_d = storage.make_copy()
for item in test_items:
    copy_d["lastBookingId"] += 1
    copy_d["bookings"].append({
        "id": copy_d["lastBookingId"],
        "userId": 123456,
        "userName": "Тестовий Студент",
        "tableNum": item["tableNum"],
        "hours": item["hours"],
        "createdAt": item["createdAt"]
    })

storage.save_changes(copy_d)
print("✅ Згенеровано 8 тестових бронювань!")