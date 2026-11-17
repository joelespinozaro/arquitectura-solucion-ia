"""M5S2 · Parte 1: la traza usa nuestro trace_id y no rompe nada si LangSmith falta."""
import json
import subprocess
import sys
import uuid
from pathlib import Path

from src.utils import observability

PROBE = Path(__file__).with_name("_probe_langsmith.py")


def _run_probe(tracing: str) -> dict:
    out = subprocess.run(
        [sys.executable, "-I", str(PROBE), tracing],
        capture_output=True, text=True, timeout=60, check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_trace_config_usa_el_trace_id_como_run_id():
    tid = str(uuid.uuid4())
    cfg = observability.trace_config(tid, "S1", "joel", tags=["chat"])
    assert cfg["run_id"] == uuid.UUID(tid)
    assert cfg["metadata"] == {"session_id": "S1", "user": "joel"}
    assert cfg["tags"] == ["instituto", "chat"]


def test_langsmith_activo_requiere_flag_y_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert observability.langsmith_activo() is False
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert observability.langsmith_activo() is False  # falta la key
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_x")
    assert observability.langsmith_activo() is True


def test_anotar_traza_es_noop_sin_tracing(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    observability.anotar_traza(guardrail_layer="x")  # no debe lanzar nada


def test_anotar_traza_no_rompe_si_el_sdk_falla(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_x")

    def boom():
        raise RuntimeError("langsmith caído")

    monkeypatch.setattr("langsmith.run_helpers.get_current_run_tree", boom)
    observability.anotar_traza(guardrail_layer="x")  # se traga el error


def test_traza_llega_con_nuestro_id_tags_metadata_y_capa_del_guardrail():
    r = _run_probe("true")
    assert r["root_found"], "la traza raíz debe tener el trace_id que fijamos"
    assert r["tags"] == ["chat", "instituto"]
    assert r["session_id"] == "SESION-1"
    assert r["steps_with_guardrail"] == ["Bloqueo.before_model"]


def test_con_tracing_apagado_no_se_envia_nada():
    r = _run_probe("false")
    assert r["requests"] == 0
