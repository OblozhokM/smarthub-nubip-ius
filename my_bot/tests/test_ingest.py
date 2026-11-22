import json
from datetime import datetime, timedelta, timezone

import ingest
import storage

from conftest import TEST_INGEST_KEY, request


def iso(delta_seconds=0):
    return (datetime.now(timezone.utc) - timedelta(seconds=delta_seconds)).isoformat()


def post_reading(app, payload, key=TEST_INGEST_KEY, raw=None):
    kwargs = {"headers": {"x-api-key": key}}
    if raw is not None:
        kwargs["data"] = raw
        kwargs["headers"]["Content-Type"] = "application/json"
    else:
        kwargs["json"] = payload
    return request(app, "POST", "/readings", **kwargs)


def test_is_valid_time():
    assert ingest.is_valid_time(None) is False
    assert ingest.is_valid_time("2026-11-21T10:00:00") is False  # без часового поясу
    assert ingest.is_valid_time(iso(60)) is True
    assert ingest.is_valid_time("не час") is False
    assert ingest.is_valid_time((datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()) is True
    assert ingest.is_valid_time((datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()) is False
    assert ingest.is_valid_time(iso(8 * 24 * 3600)) is False


def test_readings_rejects_wrong_key(app):
    status, _, _ = post_reading(app, {"sensor": "зона-1", "value": 22, "time": iso()}, key="wrong")
    assert status == 401


def test_readings_rejects_invalid_json_and_shape(app):
    status, _, _ = post_reading(app, None, raw="{sensor:")
    assert status == 400
    status, _, _ = post_reading(app, [1, 2, 3])
    assert status == 400


def test_readings_validates_sensor_and_value(app):
    base = {"sensor": "зона-1", "value": 22, "time": iso()}
    for bad in (
        {**base, "sensor": ""},
        {**base, "sensor": "x" * 31},
        {**base, "value": True},
        {**base, "value": "22"},
        {**base, "time": iso(8 * 24 * 3600)},
    ):
        assert post_reading(app, bad)[0] == 400


def test_readings_success_and_duplicate(app):
    payload = {"sensor": "зона-1", "value": 23.4, "time": iso(30)}
    status, _, body = post_reading(app, payload)
    assert status == 201
    assert json.loads(body)["ok"] is True

    status, _, body = post_reading(app, payload)
    assert status == 200
    assert json.loads(body)["duplicate"] is True
    assert len(storage.list_readings(sensor="зона-1")) == 1


def test_readings_rejects_huge_body(app):
    status, _, _ = post_reading(app, None, raw="x" * (10 * 1024 + 1))
    assert status == 413


def test_create_app_registers_routes(app):
    assert request(app, "GET", "/невідомий")[0] == 404
    assert post_reading(app, {"sensor": "зона-2", "value": 21, "time": iso()})[0] == 201
