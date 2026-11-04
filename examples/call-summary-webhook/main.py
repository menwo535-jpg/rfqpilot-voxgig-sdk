"""Small synthetic-data webhook assessment; no external services or patient data."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

MAX_BODY_BYTES = 16 * 1024
KEY_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


class CallSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    caller_name: str = Field(min_length=1, max_length=120, strict=True)
    phone: str = Field(pattern=r"^\+[1-9][0-9]{5,14}$", strict=True)
    reason: str = Field(min_length=1, max_length=1000, strict=True)
    requested_time: AwareDatetime

    @field_validator("requested_time", mode="before")
    @classmethod
    def require_iso_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("Use an ISO 8601 string with a timezone offset or Z")
        return value

    @field_validator("requested_time")
    @classmethod
    def utc_time(cls, value: datetime):
        return value.astimezone(timezone.utc)


def connect(database: Path):
    return sqlite3.connect(str(database), timeout=5)


def initialize(database: Path):
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(database)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS call_summaries (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                payload_hash TEXT NOT NULL,
                caller_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                reason TEXT NOT NULL,
                requested_time TEXT NOT NULL,
                received_at TEXT NOT NULL
            )
        """)
        connection.commit()


def store_call(database: Path, key: str, payload: dict):
    """The unique key and transaction arbitrate concurrent retries atomically."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    record_id = str(uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    with closing(connect(database)) as connection:
        with connection:
            inserted = connection.execute("""
                INSERT INTO call_summaries
                    (id, idempotency_key, payload_hash, caller_name, phone, reason,
                     requested_time, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO NOTHING
            """, (record_id, key, fingerprint, payload["caller_name"], payload["phone"],
                  payload["reason"], payload["requested_time"], received_at)).rowcount == 1
            row = connection.execute(
                "SELECT id, payload_hash, received_at FROM call_summaries WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("Stored event was not found")
            if row[1] != fingerprint:
                return 409, {"detail": "Idempotency-Key was already used for different content"}
            return (201 if inserted else 200), {
                "id": row[0], "duplicate": not inserted, "received_at": row[2],
            }


def create_app(database: str | Path, token: str) -> FastAPI:
    if not isinstance(token, str) or len(token) < 16:
        raise ValueError("Set WEBHOOK_TOKEN to a secret of at least 16 characters")
    database = Path(database).resolve()
    initialize(database)
    app = FastAPI(title="Call Summary Webhook Sample", version="1.0.0")

    @app.get("/health")
    def health():
        try:
            with closing(connect(database)) as connection:
                connection.execute("SELECT 1 FROM call_summaries LIMIT 1").fetchall()
        except sqlite3.Error:
            raise HTTPException(503, "Storage temporarily unavailable") from None
        return {"status": "ok"}

    @app.post("/webhooks/call-summary")
    async def receive(request: Request):
        supplied = request.headers.get("authorization", "")
        expected = "Bearer " + token
        if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise HTTPException(415, "Use Content-Type: application/json")
        key = request.headers.get("idempotency-key", "")
        if not KEY_PATTERN.fullmatch(key):
            raise HTTPException(400, "Provide a stable Idempotency-Key (1-128 letters, digits, . _ : or -)")
        length = request.headers.get("content-length")
        if length is not None:
            try:
                size = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid Content-Length") from None
            if size < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if size > MAX_BODY_BYTES:
                raise HTTPException(413, "Request body exceeds 16 KiB")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BODY_BYTES:
                raise HTTPException(413, "Request body exceeds 16 KiB")
        try:
            decoded = json.loads(raw)
        except (ValueError, UnicodeError):
            raise HTTPException(400, "Invalid JSON") from None
        try:
            summary = CallSummary.model_validate(decoded)
        except ValidationError as error:
            # Field errors are useful; submitted caller data is not echoed back.
            detail = [{"field": ".".join(map(str, e["loc"])), "error": e["type"]}
                      for e in error.errors(include_input=False, include_url=False)]
            return JSONResponse({"detail": detail}, status_code=422)
        try:
            status, response = await run_in_threadpool(
                store_call, database, key, summary.model_dump(mode="json"),
            )
        except sqlite3.Error:
            raise HTTPException(503, "Storage temporarily unavailable; retry with the same key") from None
        return JSONResponse(response, status_code=status)

    return app


def application():
    """uvicorn main:application --factory --host 127.0.0.1 --port 8000"""
    return create_app(os.environ.get("WEBHOOK_DB", "data/calls.sqlite3"), os.environ.get("WEBHOOK_TOKEN", ""))
