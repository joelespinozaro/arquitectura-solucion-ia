"""Envía feedback con el SDK REAL de LangSmith contra un servidor falso local."""
import gzip
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PROJECT_ID = str(uuid.uuid4())
got: list = []
INFO = (
    b'{"version":"0.9","batch_ingest_config":{"use_multipart_endpoint":false,'
    b'"scale_up_qsize_trigger":1000,"scale_up_nthreads_limit":1,"scale_down_nempty_trigger":4,'
    b'"size_limit":100,"size_limit_bytes":20971520},"instance_flags":{}}'
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith(("/projects", "/sessions")):
            proyecto = {"id": PROJECT_ID, "name": "probe", "start_time": "2026-01-01T00:00:00",
                        "tenant_id": str(uuid.uuid4()), "reference_dataset_id": None}
            self._send(json.dumps([proyecto]).encode())
        else:
            self._send(INFO)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        got.append((self.path, json.loads(raw) if raw else {}))
        self._send(json.dumps({"id": str(uuid.uuid4()), "key": "x", "created_at": "2026-01-01T00:00:00",
                               "modified_at": "2026-01-01T00:00:00"}).encode())


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(
    LANGSMITH_TRACING="true", LANGSMITH_API_KEY="lsv2_test", LANGSMITH_PROJECT="probe",
    LANGSMITH_ENDPOINT=f"http://127.0.0.1:{server.server_port}",
)
from src.utils.observability import enviar_feedback  # noqa: E402

tid = str(uuid.uuid4())
ok = enviar_feedback(tid, "user_feedback", 0, "error_type_id=2 | se inventó el precio")
time.sleep(2.5)
fb = [b for p, b in got if p.startswith("/feedback")]
print(json.dumps({
    "enviado": ok,
    "feedback_posts": len(fb),
    "run_id_ok": bool(fb) and fb[0].get("run_id") == tid,
    "session_id_ok": bool(fb) and fb[0].get("session_id") == PROJECT_ID,
    "key": fb[0].get("key") if fb else None,
    "score": fb[0].get("score") if fb else None,
}))
