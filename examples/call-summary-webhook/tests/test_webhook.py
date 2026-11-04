import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from main import MAX_BODY_BYTES, create_app

TOKEN = "unit-test-token-not-a-real-secret"
SAMPLE = {"caller_name": "Sample Caller", "phone": "+12025550123",
          "reason": "Demo appointment request", "requested_time": "2030-01-15T10:30:00+08:00"}


def headers(key="sample-call-001"):
    return {"Authorization": "Bearer " + TOKEN, "Idempotency-Key": key}


@pytest.fixture
def setup(tmp_path):
    database = tmp_path / "calls.sqlite3"
    with TestClient(create_app(database, TOKEN)) as client:
        yield client, database


def row_count(database):
    with closing(sqlite3.connect(database)) as db:
        return db.execute("SELECT COUNT(*) FROM call_summaries").fetchone()[0]


def test_create_and_persist_every_field(setup):
    client, database = setup
    result = client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    assert result.status_code == 201 and result.json()["duplicate"] is False
    datetime.fromisoformat(result.json()["received_at"])
    with closing(sqlite3.connect(database)) as db:
        row = db.execute("SELECT caller_name, phone, reason, requested_time FROM call_summaries").fetchone()
    assert row == (SAMPLE["caller_name"], SAMPLE["phone"], SAMPLE["reason"], "2030-01-15T02:30:00Z")


def test_retry_returns_original_id_and_time_without_second_row(setup):
    client, database = setup
    first = client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    retry = client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    assert retry.status_code == 200 and retry.json()["duplicate"] is True
    assert retry.json()["id"] == first.json()["id"]
    assert retry.json()["received_at"] == first.json()["received_at"]
    assert row_count(database) == 1


def test_key_reuse_with_different_content_is_conflict(setup):
    client, database = setup
    client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    result = client.post("/webhooks/call-summary", json={**SAMPLE, "reason": "Different request"}, headers=headers())
    assert result.status_code == 409 and row_count(database) == 1


def test_same_content_different_call_id_is_a_distinct_call(setup):
    client, database = setup
    for key in ("call-1", "call-2"):
        assert client.post("/webhooks/call-summary", json=SAMPLE, headers=headers(key)).status_code == 201
    assert row_count(database) == 2


def test_equivalent_offsets_and_name_whitespace_are_same_event(setup):
    client, database = setup
    client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    normalized = {**SAMPLE, "caller_name": "  Sample Caller  ", "requested_time": "2030-01-15T02:30:00Z"}
    assert client.post("/webhooks/call-summary", json=normalized, headers=headers()).status_code == 200
    assert row_count(database) == 1


def test_concurrent_retries_write_exactly_once(setup):
    client, database = setup
    def submit(_):
        return client.post("/webhooks/call-summary", json=SAMPLE, headers=headers("concurrent-call"))
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(submit, range(20)))
    assert sorted(r.status_code for r in results) == [200] * 19 + [201]
    assert len({r.json()["id"] for r in results}) == 1
    assert row_count(database) == 1


def test_retry_survives_process_app_restart(setup):
    client, database = setup
    first = client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    with TestClient(create_app(database, TOKEN)) as restarted:
        retry = restarted.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    assert retry.status_code == 200 and retry.json()["id"] == first.json()["id"]
    assert row_count(database) == 1


@pytest.mark.parametrize("field,value", [
    ("caller_name", "  "), ("caller_name", "a" * 121), ("caller_name", 123),
    ("phone", "202-555-0123"), ("phone", "+" + "1" * 16), ("phone", "+0123456"),
    ("reason", " "), ("reason", "x" * 1001),
    ("requested_time", "2030-01-15T10:30:00"), ("requested_time", "not-a-date"),
    ("requested_time", 1894703400),
])
def test_validation_rejects_bad_fields_without_writing(setup, field, value):
    client, database = setup
    response = client.post("/webhooks/call-summary", json={**SAMPLE, field: value}, headers=headers())
    assert response.status_code == 422 and row_count(database) == 0
    assert all("input" not in error for error in response.json()["detail"])


@pytest.mark.parametrize("payload", [{}, [], {**SAMPLE, "extra": True}])
def test_missing_fields_wrong_shape_and_unknown_fields(setup, payload):
    client, database = setup
    assert client.post("/webhooks/call-summary", json=payload, headers=headers()).status_code == 422
    assert row_count(database) == 0


def test_authentication_is_required_and_precedes_body_validation(setup):
    client, database = setup
    for auth in ({}, {"Authorization": "Bearer wrong"}):
        response = client.post("/webhooks/call-summary", content=b"broken", headers=auth)
        assert response.status_code == 401
    assert row_count(database) == 0


def test_bad_json_content_type_keys_and_body_limits(setup):
    client, database = setup
    h = {**headers(), "Content-Type": "application/json"}
    assert client.post("/webhooks/call-summary", content=b"{", headers=h).status_code == 400
    assert client.post("/webhooks/call-summary", content=b"\xff", headers=h).status_code == 400
    assert client.post("/webhooks/call-summary", content=b"{}", headers={**headers(), "Content-Type": "text/plain"}).status_code == 415
    assert client.post("/webhooks/call-summary", json=SAMPLE, headers={"Authorization": "Bearer " + TOKEN}).status_code == 400
    assert client.post("/webhooks/call-summary", json=SAMPLE, headers=headers("x" * 129)).status_code == 400
    assert client.post("/webhooks/call-summary", content=b" " * (MAX_BODY_BYTES + 1), headers=h).status_code == 413
    def chunks():
        yield b" " * MAX_BODY_BYTES
        yield b"x"
    assert client.post("/webhooks/call-summary", content=chunks(), headers=h).status_code == 413
    assert row_count(database) == 0


def test_storage_error_is_retryable_and_does_not_echo_payload(setup):
    client, database = setup
    with closing(sqlite3.connect(database)) as db:
        db.execute("DROP TABLE call_summaries")
        db.commit()
    response = client.post("/webhooks/call-summary", json=SAMPLE, headers=headers())
    assert response.status_code == 503
    assert SAMPLE["phone"] not in response.text
    assert client.get("/health").status_code == 503


@pytest.mark.parametrize('name', ['示例来电者', "Sample'); DROP TABLE call_summaries; --"])
def test_unicode_and_sql_like_names_are_stored_as_data(setup, name):
    client, database = setup
    response = client.post('/webhooks/call-summary', json={**SAMPLE, 'caller_name': name}, headers=headers())
    assert response.status_code == 201
    with closing(sqlite3.connect(database)) as db:
        assert db.execute('SELECT caller_name FROM call_summaries').fetchone()[0] == name
    assert row_count(database) == 1


def test_health_and_configuration(setup, tmp_path):
    client, _ = setup
    assert client.get("/health").json() == {"status": "ok"}
    with pytest.raises(ValueError):
        create_app(tmp_path / "unused.sqlite3", "short")
