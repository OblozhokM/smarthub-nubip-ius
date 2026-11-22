from utils import csv_parser
from utils.validators import (
    is_valid_date,
    parse_count,
    parse_hours,
    parse_id,
    parse_json,
    parse_minutes,
    parse_number,
    validate_phone,
    validate_qr_code,
)


def test_parse_number():
    assert parse_number("3,5") == 3.5
    assert parse_number("-2") == -2.0
    assert parse_number(None) is None
    assert parse_number("nan") is None
    assert parse_number("inf") is None
    assert parse_number("abc") is None


def test_parse_id():
    assert parse_id("12") == 12
    assert parse_id("0") is None
    assert parse_id("-1") is None
    assert parse_id("x") is None


def test_parse_hours():
    assert parse_hours(None) == 24.0
    assert parse_hours("3,5") == 3.5
    assert parse_hours("0") is None
    assert parse_hours("721") is None


def test_parse_count_and_minutes():
    assert parse_count(None) == 5
    assert parse_count("7") == 7
    assert parse_count("21") is None
    assert parse_minutes("10") == 10
    assert parse_minutes("10081") is None
    assert parse_minutes(None) is None


def test_is_valid_date_checks_calendar():
    assert is_valid_date("21.11.2026") is True
    assert is_valid_date("29.02.2024") is True
    assert is_valid_date("29.02.2026") is False
    assert is_valid_date("31.04.2026") is False
    assert is_valid_date("21.11.26") is False
    assert is_valid_date("") is False
    assert is_valid_date("aa.bb.cccc") is False


def test_parse_json():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json("broken") is None
    assert parse_json(None) is None


def test_phone_and_qr():
    assert validate_phone("0671234567") is True
    assert validate_phone("067123456") is False
    assert validate_qr_code("hub-05") is True
    assert validate_qr_code("HUB-5") is False


def test_csv_parsing():
    text = "стіл,години\n1,2\n11,3\n2,bad\n3,4\n"
    result = csv_parser.bookings_from_csv(text)
    assert result["good"] == [
        {"tableNum": 1, "hours": 2.0},
        {"tableNum": 3, "hours": 4.0},
    ]
    assert len(result["errors"]) == 2
    assert csv_parser.read_csv_file(__import__("pathlib").Path("/немає/файлу.csv")) is None
