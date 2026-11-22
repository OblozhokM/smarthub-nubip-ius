import storage
from utils.format import (
    format_booking,
    format_period_report,
    format_stats_report,
)
from utils.stats import calc_stats, group_by_table, top_values


def test_booking_crud(bookings):
    assert storage.get_booking(2)["hours"] == 6.0
    storage.update_booking(2, hours=8.0)
    assert storage.get_booking(2)["hours"] == 8.0
    assert storage.delete_booking(3)["id"] == 3
    assert storage.list_bookings() == [storage.get_booking(2), storage.get_booking(1)]


def test_user_bookings_are_separate_from_readings(readings, bookings):
    assert len(storage.get_user_bookings(101)) == 2
    assert len(storage.list_bookings()) == 3
    assert all(b["userId"] != 0 for b in storage.list_bookings())


def test_format_booking_handles_zulu_timestamp():
    record = {
        "id": 7, "userName": "Аня", "tableNum": 4, "hours": 2.0,
        "createdAt": "2026-11-21T10:00:00Z",
    }
    text = format_booking(record)
    assert "#7" in text
    assert "Стіл №4" in text
    assert "12:00:00" in text  # Київ = UTC+2


def test_calc_stats_and_grouping():
    records = [
        {"tableNum": 1, "hours": 2.0},
        {"tableNum": 1, "hours": 4.0},
        {"tableNum": 2, "hours": 3.0},
    ]
    assert calc_stats([]) is None
    assert calc_stats(records) == {"count": 3, "min": 2.0, "max": 4.0, "avg": 3.0}
    groups = group_by_table(records)
    assert set(groups) == {"Стіл №1", "Стіл №2"}
    assert [r["id"] for r in top_values([{"id": 1, "hours": 1}, {"id": 2, "hours": 5}], 1)] == [2]


def test_report_formatters():
    assert "записів немає" in format_period_report("Тест", [])
    assert "записів немає" in format_stats_report("Тест", [])
    records = [{"id": 1, "tableNum": 1, "hours": 2.0, "createdAt": "2026-11-21T10:00:00Z"}]
    assert "Тест" in format_period_report("Тест", records)
    assert "Стіл №1" in format_stats_report("Тест", records)
