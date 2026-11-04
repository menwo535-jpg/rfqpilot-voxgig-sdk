# Call summary webhook sample

A small Python/FastAPI endpoint that validates a receptionist call summary,
stores it in SQLite, and handles webhook retries without duplicate rows.
This is an independent assessment sample using fictional data, not a client
deployment or a system for processing patient information.

## Run

Python 3.11 or newer. To obtain this isolated sample branch:

```sh
git clone --branch samples/call-summary-webhook --single-branch https://github.com/menwo535-jpg/rfqpilot-voxgig-sdk.git
cd rfqpilot-voxgig-sdk/examples/call-summary-webhook
```

Work from this directory:

```sh
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
export WEBHOOK_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn main:application --factory --host 127.0.0.1 --port 8000
```

Windows PowerShell alternative, without activating scripts:

```powershell
$venvPython = '.venv/Scripts/python.exe'
& $venvPython -m pip install -r requirements.txt
$env:WEBHOOK_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
& $venvPython -m uvicorn main:application --factory --host 127.0.0.1 --port 8000
```

The token must contain at least 16 characters. Keep it private and configure
the same token on the sender. `WEBHOOK_DB` optionally selects the SQLite file;
the default is `data/calls.sqlite3`. It is created automatically and ignored by Git.

## Request

`POST /webhooks/call-summary`

```sh
curl http://127.0.0.1:8000/webhooks/call-summary \
  -H "Authorization: Bearer $WEBHOOK_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-call-001' \
  -d '{"caller_name":"Sample Caller","phone":"+12025550123","reason":"Demo appointment request","requested_time":"2030-01-15T10:30:00+08:00"}'
```

Use `curl.exe` in Windows PowerShell, or an HTTP client of your choice.
The example name, number and request are fictional.

| Field | Validation |
|---|---|
| `caller_name` | Nonblank string, at most 120 characters; surrounding whitespace removed |
| `phone` | International `+` form, 6–15 ASCII digits, first digit nonzero; format check only, not number ownership/availability |
| `reason` | Nonblank string, at most 1,000 characters |
| `requested_time` | ISO 8601 string with `Z` or a timezone offset; stored in UTC |

Unknown fields are rejected. The total body is limited to 16 KiB, including
streamed requests. Historical timestamps are permitted; the endpoint stores
a requested time and does not book an appointment.

## Responses and retries

| Status | Meaning |
|---|---|
| `201` | First accepted delivery; returns `id`, `duplicate:false`, and UTC `received_at` |
| `200` | Same key and normalized content retried; returns the original ID/time and `duplicate:true` |
| `400` | Missing/invalid idempotency key or malformed JSON |
| `401` | Missing/incorrect bearer token; body is not processed |
| `409` | An existing key was reused with different content |
| `413` | Body larger than 16 KiB |
| `415` | Content type is not `application/json` |
| `422` | Invalid/missing fields or unknown fields; submitted caller values are not echoed |
| `503` | Storage unavailable; retry with the same key |

The sender must reuse a stable call/event ID as `Idempotency-Key` on retries
(1–128 letters, digits, `.`, `_`, `:` or `-`). A phone number is not a call ID:
two genuine calls with identical summaries but different event IDs remain
two records. UTC normalization and trimmed name/reason whitespace avoid
false conflicts for equivalent retries.

SQLite's unique constraint and transaction arbitrate concurrent deliveries.
Deduplication survives application restarts. No in-memory-only retry cache is
used. Records contain all four validated fields, a payload hash, the event key,
the record ID and the receipt timestamp. SQL values are parameterized.

`GET /health` checks database access and returns only `{"status":"ok"}`.
There is no public endpoint for listing caller records. The sample does not
log request bodies or invoke any external API, model or service.

## Verify

```sh
python -m pytest -q
python smoke_http.py
```

The tests cover persistence, sequential and 20 concurrent retries, conflicting
key reuse, distinct calls, equivalent timezone offsets, restart recovery,
validation, authentication, body limits, malformed input and storage failure.
`smoke_http.py` starts a real localhost Uvicorn process, checks the HTTP
contract, restarts it against the same database and checks deduplication again.
It uses a temporary database and stops only its own process.

Validated on Windows / Python 3.11.13. These tests verify the sample contract;
they are not evidence of healthcare compliance or a production load test.

## Scope

For an actual deployment, the sender's event ID, authentication format and
schema need to be agreed first. HTTPS, secret rotation, data access controls,
retention, encrypted storage, monitoring and backup policies belong in that
deployment. This SQLite/local-server assessment makes no HIPAA or other
clinical-data compliance claim. Do not submit real patient information.
