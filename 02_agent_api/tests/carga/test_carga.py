"""M5S2 · Parte 4: modelo simulado, capas sin Groq en modo fake y chequeo de SLO."""
import asyncio
import csv
import importlib.util
import time
from pathlib import Path

import pytest
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from src.services import guardrails
from src.services.guardrails.layer7_prompt_guard import PromptGuardMiddleware
from src.services.guardrails.layer8_llama_guard import LlamaGuardMiddleware
from src.utils.modelo_simulado import RESPUESTA, ModeloSimulado

RAIZ = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("check_slo", RAIZ / "loadtest" / "check_slo.py")
check_slo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_slo)


def test_modelo_simulado_responde_tras_la_demora_y_reporta_tokens():
    agente = create_agent(model=ModeloSimulado(delay_ms=120), tools=[])
    t0 = time.perf_counter()
    r = asyncio.run(agente.ainvoke({"messages": [HumanMessage(content="hola")]}))
    ms = (time.perf_counter() - t0) * 1000
    ultimo = r["messages"][-1]
    assert ultimo.content == RESPUESTA
    assert ultimo.usage_metadata["input_tokens"] == 120
    assert ms >= 110, "debe respetar la demora configurada"


def test_modelo_simulado_acepta_tools_sin_llamarlas():
    m = ModeloSimulado()
    assert m.bind_tools([object()]) is m


def test_en_modo_fake_no_hay_capas_que_llamen_a_groq(monkeypatch):
    monkeypatch.setattr(guardrails, "LLM_MODE", "fake")
    capas = guardrails.build_input_guardrails()
    assert capas, "las capas regex siguen activas"
    assert not any(isinstance(c, (PromptGuardMiddleware, LlamaGuardMiddleware)) for c in capas)


def test_en_modo_real_siguen_las_capas_de_groq(monkeypatch):
    monkeypatch.setattr(guardrails, "LLM_MODE", "real")
    monkeypatch.setattr(guardrails, "GUARDRAIL_ENGINE", "local")
    capas = guardrails.build_input_guardrails()
    assert any(isinstance(c, PromptGuardMiddleware) for c in capas)
    assert any(isinstance(c, LlamaGuardMiddleware) for c in capas)


def _csv(tmp_path, total, fallas, p50, p95, p99):
    ruta = tmp_path / "stats.csv"
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Name", "Request Count", "Failure Count", "50%", "95%", "99%"])
        w.writeheader()
        w.writerow({"Name": "chat: programas", "Request Count": 1, "Failure Count": 0, "50%": 1, "95%": 1, "99%": 1})
        w.writerow({"Name": "Aggregated", "Request Count": total, "Failure Count": fallas, "50%": p50, "95%": p95, "99%": p99})
    return str(ruta)


def test_slo_cumple(tmp_path):
    ok, msg = check_slo.evaluar(_csv(tmp_path, 100, 0, 900, 1600, 1800))
    assert ok and "CUMPLE" in msg and "NO CUMPLE" not in msg


def test_slo_falla_por_latencia(tmp_path):
    ok, msg = check_slo.evaluar(_csv(tmp_path, 100, 0, 3000, 4500, 4600))
    assert not ok and "SLO latencia (p95 <= 2000 ms): NO CUMPLE" in msg


def test_slo_falla_por_errores(tmp_path):
    ok, msg = check_slo.evaluar(_csv(tmp_path, 100, 5, 900, 1500, 1600))
    assert not ok and "SLO errores (<= 1%): NO CUMPLE" in msg


def test_slo_sin_fila_agregada(tmp_path):
    ruta = tmp_path / "vacio.csv"
    ruta.write_text("Name,Request Count,Failure Count,50%,95%,99%\n", encoding="utf-8")
    ok, msg = check_slo.evaluar(str(ruta))
    assert not ok and "Aggregated" in msg
