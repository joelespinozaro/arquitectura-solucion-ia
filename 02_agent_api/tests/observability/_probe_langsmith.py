"""Corre un agente con un LangSmith FALSO (servidor local) y imprime qué llegó.

Se ejecuta en un subproceso (python -I) para que la configuración global del SDK
de LangSmith no contamine al resto de los tests. No usa red ni keys reales.
"""
import asyncio
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

got: list = []
INFO = (
    b'{"version":"0.9","batch_ingest_config":{"use_multipart_endpoint":false,'
    b'"scale_up_qsize_trigger":1000,"scale_up_nthreads_limit":1,"scale_down_nempty_trigger":4,'
    b'"size_limit":100,"size_limit_bytes":20971520},"instance_flags":{}}'
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ok(self, body=b"{}"):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._ok(INFO)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        got.append(json.loads(raw) if raw else {})
        self._ok()


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(
    LANGSMITH_TRACING=sys.argv[1],
    LANGSMITH_API_KEY="lsv2_test",
    LANGSMITH_ENDPOINT=f"http://127.0.0.1:{server.server_port}",
    LANGSMITH_PROJECT="probe",
)

from langchain.agents import create_agent  # noqa: E402
from langchain.agents.middleware import AgentMiddleware  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from src.utils.observability import anotar_traza, trace_config  # noqa: E402


class Bloqueo(AgentMiddleware):
    def before_model(self, state, runtime):
        anotar_traza(guardrail_layer="layer2_prompt_injection", guardrail_blocked=True)
        return None


class Modelo(FakeMessagesListChatModel):
    def bind_tools(self, *a, **k):
        return self


agent = create_agent(model=Modelo(responses=[AIMessage(content="ok")]), tools=[], middleware=[Bloqueo()])
trace_id = str(uuid.uuid4())
asyncio.run(
    agent.ainvoke(
        {"messages": [HumanMessage(content="hola")]},
        config=trace_config(trace_id, "SESION-1", "joel", tags=["chat"]),
    )
)
time.sleep(2.5)

runs = [r for g in got for k in ("post", "patch") for r in g.get(k, [])]
meta = lambda r: (r.get("extra") or {}).get("metadata", {})  # noqa: E731
root = [r for r in runs if r.get("id") == trace_id]
print(
    json.dumps(
        {
            "requests": len(got),
            "root_found": bool(root),
            "tags": sorted(root[0].get("tags") or []) if root else [],
            "session_id": meta(root[0]).get("session_id") if root else None,
            "steps_with_guardrail": [r.get("name") for r in runs if meta(r).get("guardrail_layer")],
        }
    )
)
