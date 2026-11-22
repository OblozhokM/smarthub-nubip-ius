import json
from datetime import datetime, timedelta, timezone

import config
import storage


def iso(delta_minutes=0):
    return (datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)).isoformat()


def test_default_data_shape():
    data = storage._default_data()
    assert set(data) == {
        "users", "bookings", "lastBookingId", "subscriptions",
        "reminders", "lastReminderId", "lastReportDay",
    }
    assert data["bookings"] == []


def test_save_and_load_roundtrip():
    payload = storage._default_data()
    payload["lastReportDay"] = "21.11.2026"
    storage.save_data(payload)
    loaded = storage.load_data()
    assert loaded["lastReportDay"] == "21.11.2026"
    with open(config.DATA_FILE, encoding="utf-8") as f:
        assert json.load(f)["lastReportDay"] == "21.11.2026"


def test_atomic_save_removes_tmp_file():
    storage.save_data(storage._default_data())
    assert not config.DATA_FILE.with_suffix(".json.tmp").exists()


def test_corrupted_json_does_not_poison_memory():
    config.DATA_FILE.write_text("{broken", encoding="utf-8")
    loaded = storage.load_data()
    assert loaded == storage._default_data()


def test_make_copy_is_deep():
    storage.add_booking(1, "Аня", 1, 2.0)
    snapshot = storage.make_copy()
    snapshot["bookings"][0]["hours"] = 99
    assert storage.get_booking(1)["hours"] == 2.0


def test_save_changes_replaces_state():
    payload = storage._default_data()
    payload["lastBookingId"] = 42
    storage.save_changes(payload)
    assert storage.load_data()["lastBookingId"] == 42


def test_user_created_and_updated():
    user = storage.get_user(555)
    assert user["city"] == "Київ"
    updated = storage.save_user(555, name="Олег", phone="0671234567", city="Львів")
    assert updated["name"] == "Олег"
    assert storage.get_user(555)["phone"] == "0671234567"


def test_add_booking_assigns_ids(bookings):
    assert [b["id"] for b in bookings] == [1, 2, 3]
    assert bookings[1]["tableNum"] == 2
    assert bookings[0]["userName"] == "Аня"


def test_get_and_list_bookings_exclude_readings(readings, bookings):
    assert len(storage.list_bookings()) == 3
    assert len(storage.list_bookings(include_readings=True)) > 3
    assert storage.get_booking(1)["tableNum"] == 1
    assert storage.get_booking(999) is None


def test_get_user_bookings(bookings):
    assert [b["id"] for b in storage.get_user_bookings(101)] == [1, 3]
    assert storage.get_user_bookings(999) == []


def test_update_booking(bookings):
    updated = storage.update_booking(2, hours=7.5, tableNum=5)
    assert updated["hours"] == 7.5
    assert updated["tableNum"] == 5
    assert storage.update_booking(999, hours=1) is None


def test_delete_booking_respects_owner(bookings):
    assert storage.delete_booking(1, user_id=102) is None
    removed = storage.delete_booking(1, user_id=101)
    assert removed["id"] == 1
    assert storage.get_booking(1) is None


def test_add_device_reading_deduplicates():
    timestamp = iso(30)
    first = storage.add_device_reading("зона-1", 22.0, timestamp)
    duplicate = storage.add_device_reading("зона-1", 22.0, timestamp)
    assert first is not None
    assert duplicate is None


def test_add_device_reading_keeps_chronological_order():
    storage.add_device_reading("зона-1", 21.0, iso(60))
    storage.add_device_reading("зона-1", 23.0, iso(5))
    storage.add_device_reading("зона-1", 22.0, iso(30))
    times = [r["createdAt"] for r in storage.data["bookings"]]
    assert times == sorted(times)


def test_latest_by_sensor_ignores_bookings(readings, bookings):
    latest = storage.latest_by_sensor()
    assert set(latest) == {"теплиця-1", "теплиця-2", "<b>x</b>", "constructor", "одне-читання"}
    assert latest["теплиця-1"]["hours"] == 35.0


def test_list_readings_last_hours(readings):
    items = storage.list_readings_last_hours(6)
    assert len(items) == 9
    assert all(set(item) == {"sensor", "value", "createdAt"} for item in items)


def test_list_bookings_last_hours_with_fixed_now():
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    storage.add_booking(1, "Аня", 1, 2.0)
    storage.data["bookings"][0]["createdAt"] = (now - timedelta(hours=1)).isoformat()
    storage.save_data()
    assert len(storage.list_bookings_last_hours(2, now)) == 1
    assert storage.list_bookings_last_hours(2, now + timedelta(hours=3)) == []


def test_list_bookings_by_day_uses_kyiv_time():
    storage.add_booking(1, "Аня", 1, 2.0)
    storage.data["bookings"][0]["createdAt"] = "2026-11-21T23:30:00+00:00"
    storage.save_data()
    assert len(storage.list_bookings_by_day("22.11.2026")) == 1
    assert storage.list_bookings_by_day("21.11.2026") == []
    assert storage.list_bookings_by_day("не дата") == []


def test_list_top_bookings(bookings):
    top = storage.list_top_bookings(2)
    assert [r["id"] for r in top] == [2, 1]


def test_add_many_bookings_uses_one_id_sequence():
    created = storage.add_many_bookings(1, "Імя", [
        {"tableNum": 1, "hours": 2.0},
        {"tableNum": 2, "hours": 3.0},
    ])
    assert [r["id"] for r in created] == [1, 2]
    assert storage.data["lastBookingId"] == 2


def test_subscriptions():
    assert storage.add_subscriber("news", 7) is True
    assert storage.add_subscriber("news", 7) is False
    assert storage.is_subscribed("news", 7) is True
    assert storage.get_user_subscriptions(7) == ["news"]
    assert storage.remove_subscriber("news", 7) is True
    assert storage.list_subscribers("news") == []


def test_reminders_lifecycle():
    rem = storage.add_reminder(7, "Дзвінок", "2026-11-21T10:00:00+00:00")
    assert rem["sent"] is False
    assert storage.get_user_reminders(7) == [rem]
    assert storage.get_due_reminders("2026-11-21T11:00:00+00:00") == [rem]
    storage.mark_reminder_sent(rem["id"])
    assert storage.get_user_reminders(7) == []
    assert storage.remove_reminder(rem["id"]) is True


def test_delete_reminder_checks_owner():
    rem = storage.add_reminder(7, "Текст", "2026-11-22T10:00:00+00:00")
    assert storage.delete_reminder(rem["id"], 8) is False
    assert storage.delete_reminder(rem["id"], 7) is True


def test_report_day():
    assert storage.get_last_report_day() == ""
    assert storage.set_last_report_day("21.11.2026") == "21.11.2026"
    assert storage.get_last_report_day() == "21.11.2026"


# --- 15 нових функцій ---

def test_normalize_reading():
    storage.add_booking(1, "Аня", 1, 2.0)
    assert storage.normalize_reading(storage.get_booking(1)) is None
    normalized = storage.normalize_reading(storage.add_test_reading("зона-1", 23.5, iso(1)))
    assert normalized["sensor"] == "зона-1"
    assert normalized["value"] == 23.5
    assert normalized["timeMs"] is not None


def test_list_readings_filters(readings):
    all_items = storage.list_readings()
    assert all_items[0]["sensor"] in {"теплиця-2", "constructor", "<b>x</b>", "одне-читання"}
    one = storage.list_readings(sensor="теплиця-1")
    assert len(one) == 2
    assert all(item["sensor"] == "теплиця-1" for item in one)
    filtered = storage.list_readings(since_ms=one[0]["timeMs"])
    assert len(filtered) == 2
    assert all(item["timeMs"] >= one[0]["timeMs"] for item in filtered)
    assert storage.list_readings(now_ms=0) == []


def test_list_readings_by_sensor_and_count(readings):
    two = storage.list_readings_by_sensor("теплиця-1", hours=6)
    assert len(two) == 2
    assert storage.count_readings("теплиця-1", hours=6) == 2
    assert storage.count_readings(hours=6) == 9


def test_get_sensor_names_sorted(readings, bookings):
    assert storage.get_sensor_names() == [
        "<b>x</b>", "constructor", "одне-читання", "теплиця-1", "теплиця-2",
    ]


def test_calc_sensor_stats():
    assert storage.calc_sensor_stats([]) is None
    stats = storage.calc_sensor_stats([{"value": 10}, {"value": 20}, {"hours": 30}])
    assert stats == {"count": 3, "min": 10, "avg": 20, "max": 30}


def test_group_by_sensor_handles_constructor(readings):
    grouped = storage.group_by_sensor(storage.list_readings())
    assert "constructor" in grouped
    assert len(grouped["constructor"]) == 2


def test_summarize_sensors(readings):
    summary = storage.summarize_sensors(hours=6)
    assert summary["теплиця-2"]["count"] == 2
    assert summary["теплиця-1"]["max"] == 35.0


def test_latest_readings_limit(readings):
    assert len(storage.latest_readings(3)) == 3
    assert storage.latest_readings(0) == []


def test_chart_points_oldest_first(readings):
    points = storage.chart_points("теплиця-1", hours=6)
    assert [p["value"] for p in points] == [34.8, 35.0]
    assert points[0]["time"] < points[1]["time"]


def test_stale_sensors(readings):
    storage.add_test_reading("старий", 19.0, iso(120))
    stale = storage.stale_sensors(stale_ms=30 * 60 * 1000)
    assert stale == ["старий"]


def test_dashboard_snapshot_structure(readings, bookings):
    snapshot = storage.dashboard_snapshot(hours=6)
    assert set(snapshot) == {"nowMs", "hours", "names", "latest", "summary", "recent", "series", "stale"}
    assert snapshot["names"] == storage.get_sensor_names()
    assert "constructor" in snapshot["series"]
    assert len(snapshot["recent"]) <= config.DASHBOARD_ROWS


def test_add_test_reading_and_clear_readings(readings, bookings):
    assert len(storage.list_readings()) == 9
    removed = storage.clear_readings()
    assert removed == 9
    assert storage.list_readings() == []
    assert len(storage.list_bookings()) == 3


def test_restore_data_snapshot(readings):
    snapshot = storage.make_copy()
    storage.clear_readings()
    assert storage.list_readings() == []
    storage.restore_data_snapshot(snapshot)
    assert len(storage.list_readings()) == 9
