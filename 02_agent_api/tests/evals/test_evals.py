"""M5S2 · Parte 2: feedback en la traza, juez automático y dataset de errores."""
import json
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.services import eval_service, history_service
from src.services.eval_service import (
    contexto_de, juzgar_conversaciones, parsear_veredicto, pasar_negativos_a_dataset,
)
from src.utils import observability

PROBE = Path(__file__).with_name("_probe_feedback.py")


def hist(pregunta="¿Cuánto cuesta?", respuesta="S/ 500", sources=None, **kw):
    return SimpleNamespace(
        trace_id=uuid.uuid4(), question=pregunta, answer=respuesta,
        sources=sources, error_type_id=kw.get("error_type_id"), observations=kw.get("observations"),
    )


# ── feedback ────────────────────────────────────────────────────────────────

def test_feedback_llega_con_run_id_y_session_id_del_proyecto():
    out = subprocess.run([sys.executable, "-I", str(PROBE)], capture_output=True, text=True, timeout=60, check=True)
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r == {"enviado": True, "feedback_posts": 1, "run_id_ok": True,
                 "session_id_ok": True, "key": "user_feedback", "score": 0}


def test_enviar_feedback_sin_langsmith_devuelve_false(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert observability.enviar_feedback(str(uuid.uuid4()), "user_feedback", 1) is False


def test_enviar_feedback_no_lanza_si_el_cliente_falla(monkeypatch):
    class Roto:
        def read_project(self, **kw):
            raise RuntimeError("401")

    monkeypatch.setattr(observability, "obtener_cliente", lambda: Roto())
    assert observability.enviar_feedback(str(uuid.uuid4()), "user_feedback", 1) is False


def test_guardar_feedback_tambien_lo_envia_a_la_traza(monkeypatch):
    enviados = []
    monkeypatch.setattr(history_service, "enviar_feedback", lambda *a, **k: enviados.append(a) or True)

    class Repo:
        def get_by_trace_id(self, t):
            return object()

        def save_feedback(self, **kw):
            return "guardado"

    svc = history_service.HistoryService.__new__(history_service.HistoryService)
    svc._repo = Repo()
    assert svc.save_feedback("t-1", False, 2, "se inventó el precio") == "guardado"
    assert enviados == [("t-1", "user_feedback", 0, "error_type_id=2 | se inventó el precio")]


# ── juez ────────────────────────────────────────────────────────────────────

def test_parsear_veredicto():
    assert parsear_veredicto('Claro: {"score": 1, "razon": "ok"}') == {"score": 1.0, "razon": "ok"}
    assert parsear_veredicto('{"score": 0, "razon": "inventó"}')["score"] == 0.0
    assert parsear_veredicto("no sé") is None
    assert parsear_veredicto('{"score": 0.5}') is None  # solo 0 o 1


def test_contexto_de_junta_documentos_y_fichas():
    src = json.dumps([{"contexts": ["Curso de 8 semanas"], "fields": [{"label": "Estado", "value": "Matriculada"}]}])
    c = contexto_de(src)
    assert "Curso de 8 semanas" in c and "Estado: Matriculada" in c
    assert "sin contexto" in contexto_de(None)


def test_juez_puntua_y_adjunta_a_la_traza():
    llm = FakeListChatModel(responses=['{"score": 1, "razon": "cita el documento"}',
                                       '{"score": 0, "razon": "inventó el precio"}',
                                       "esto no es json"])
    enviados = []
    h = [hist(), hist(), hist()]
    r = juzgar_conversaciones(llm, h, enviar=lambda *a: enviados.append(a) or True)
    assert (r["juzgadas"], r["ok"], r["inventadas"], r["sin_veredicto"]) == (2, 1, 1, 1)
    assert [e[1] for e in enviados] == ["grounded", "grounded"]
    assert [e[2] for e in enviados] == [1.0, 0.0]


def test_juez_cuenta_los_no_enviados():
    llm = FakeListChatModel(responses=['{"score": 1, "razon": "ok"}'])
    r = juzgar_conversaciones(llm, [hist()], enviar=lambda *a: False)
    assert r["no_enviadas"] == 1


# ── dataset ─────────────────────────────────────────────────────────────────

class FakeClient:
    def __init__(self, existe=False):
        self.existe, self.creado, self.ejemplos = existe, False, None

    def has_dataset(self, dataset_name):
        return self.existe

    def create_dataset(self, nombre, **kw):
        self.creado = True

    def create_examples(self, dataset_name, examples):
        self.ejemplos = examples


def test_negativos_se_vuelven_casos_de_un_dataset():
    c = FakeClient()
    n = pasar_negativos_a_dataset([hist("¿Precio?", "S/ 999", error_type_id=2, observations="falso")], cliente=c)
    assert n == 1 and c.creado
    ej = c.ejemplos[0]
    assert ej["inputs"] == {"question": "¿Precio?"}
    assert ej["outputs"] == {"respuesta_mala": "S/ 999"}
    assert ej["metadata"]["error_type_id"] == 2


def test_dataset_existente_no_se_vuelve_a_crear():
    c = FakeClient(existe=True)
    pasar_negativos_a_dataset([hist()], cliente=c)
    assert not c.creado


def test_dataset_sin_negativos_no_hace_nada():
    assert pasar_negativos_a_dataset([], cliente=FakeClient()) == 0


def test_dataset_sin_langsmith_explica_que_hacer(monkeypatch):
    monkeypatch.setattr(eval_service, "obtener_cliente", lambda: None)
    with pytest.raises(RuntimeError, match="LANGSMITH_API_KEY"):
        pasar_negativos_a_dataset([hist()])
