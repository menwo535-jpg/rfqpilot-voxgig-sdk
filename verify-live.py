"""Start the real API on a temporary loopback port, run SDK checks, stop it."""
from pathlib import Path
import os
import secrets
import subprocess
import sys
import threading

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'api'))
from local_api import create_server

token = secrets.token_hex(24)
server = create_server(token, port=0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
env = dict(os.environ, RFQ_TEST_BASE=f'http://127.0.0.1:{server.server_port}', RFQ_TEST_TOKEN=token)
try:
    result = subprocess.run(['node', str(root / 'verify-live.cjs')], cwd=root, env=env, capture_output=True, text=True, timeout=45)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode == 0:
        (root / 'LIVE-RESULTS.json').write_text(result.stdout, encoding='utf-8')
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
sys.exit(result.returncode)
