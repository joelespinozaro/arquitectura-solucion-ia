import asyncio

import pytest
from langchain.messages import AIMessage, HumanMessage

from src.services import security_scan_service as svc
from src.services.middleware.output_guardrail import BLOCKED_RESPONSE, OutputGuardrail
from src.utils.pii import RegexPIIDetector

CANARY = "CNRY-abc123"


@pytest.fixture(autouse=True)
def detector_regex(monkeypatch):
    monkeypatch.setattr(svc, "get_shared_pii_detector", lambda: (RegexPIIDetector(), "regex"))


def state(ai):
    return {"messages": [HumanMessage(content="hola"), ai]}


def run(text, mode="off", **kw):
    mw = OutputGuardrail(pii_mode=mode, canary_token=CANARY)
    return mw.after_model(state(AIMessage(content=text, **kw)), None)


def test_respuesta_normal_no_se_toca():
    assert run("El programa dura 6 meses.") is None


def test_canary_bloquea_y_corta():
    out = run(f"Mi código interno es {CANARY}")
    assert out["jump_to"] == "end" and out["messages"][0].content == BLOCKED_RESPONSE


def test_secreto_bloquea():
    assert run("clave AKIAABCDEFGHIJKLMNOP")["jump_to"] == "end"


def test_pii_mask_reemplaza_sin_cortar():
    out = run("Escríbenos al 900000111", mode="mask")
    assert "jump_to" not in out and "900000111" not in out["messages"][0].content


def test_pii_off_deja_pasar():
    assert run("Escríbenos al 900000111", mode="off") is None


def test_pii_block():
    assert run("correo lucia@example.com", mode="block")["jump_to"] == "end"


def test_mensajes_con_tool_calls_no_se_revisan():
    ai = AIMessage(content=CANARY, tool_calls=[{"name": "x", "args": {}, "id": "1"}])
    assert OutputGuardrail(pii_mode="off", canary_token=CANARY).after_model(state(ai), None) is None


def test_async_igual_que_sync():
    mw = OutputGuardrail(pii_mode="off", canary_token=CANARY)
    out = asyncio.run(mw.aafter_model(state(AIMessage(content=CANARY)), None))
    assert out["jump_to"] == "end"


def test_el_system_prompt_incluye_el_canary():
    from src.services.agent_service import SYSTEM_PROMPT
    from src.utils.environment import CANARY_TOKEN

    assert CANARY_TOKEN in SYSTEM_PROMPT
