"""Exercise the real HTTP server with fictional input and a temporary database."""
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

import httpx


def main():
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / "calls.sqlite3"
        token = secrets.token_urlsafe(32)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "WEBHOOK_TOKEN": token, "WEBHOOK_DB": str(database)}
        base = f"http://127.0.0.1:{port}"
        payload = {"caller_name": "Sample Caller", "phone": "+12025550123",
                   "reason": "Demo appointment request", "requested_time": "2030-01-15T10:30:00+08:00"}
        headers = {"Authorization": "Bearer " + token, "Idempotency-Key": "smoke-call-001"}
        process = None

        def start():
            child = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:application", "--factory", "--host", "127.0.0.1", "--port", str(port)],
                cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(100):
                if child.poll() is not None:
                    raise RuntimeError("HTTP server exited during startup")
                try:
                    if httpx.get(base + "/health", timeout=1, trust_env=False).status_code == 200:
                        return child
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            child.terminate()
            child.wait(timeout=5)
            raise RuntimeError("HTTP server did not become ready")

        def stop(child):
            if child is not None:
                child.terminate()
                child.wait(timeout=5)

        try:
            process = start()
            with httpx.Client(base_url=base, timeout=5, trust_env=False) as client:
                first = client.post("/webhooks/call-summary", json=payload, headers=headers)
                retry = client.post("/webhooks/call-summary", json=payload, headers=headers)
                conflict = client.post("/webhooks/call-summary", json={**payload, "reason": "Different"}, headers=headers)
                invalid = client.post("/webhooks/call-summary", json={**payload, "requested_time": "2030-01-15T10:30:00"}, headers=headers)
                unauthenticated = client.post("/webhooks/call-summary", json=payload)
                assert [first.status_code, retry.status_code, conflict.status_code, invalid.status_code, unauthenticated.status_code] == [201, 200, 409, 422, 401]
                assert retry.json()["id"] == first.json()["id"] and retry.json()["duplicate"] is True
            stop(process)
            process = None
            process = start()
            again = httpx.post(base + "/webhooks/call-summary", json=payload, headers=headers, timeout=5, trust_env=False)
            assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("SELECT COUNT(*) FROM call_summaries").fetchone()[0] == 1
            print(json.dumps({"real_http": "passed", "statuses": [201, 200, 409, 422, 401],
                              "restart_retry": 200, "stored_rows": 1}))
        finally:
            stop(process)


if __name__ == "__main__":
    main()
