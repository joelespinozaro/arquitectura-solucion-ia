"""El presupuesto de tokens se acumula entre mensajes de una misma sesión."""
import asyncio

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from src.services import agent_service
from src.services.middleware import TokenBudgetMiddleware
from src.services.middleware.token_budget_middleware import BUDGET_EXCEEDED_RESPONSE


class FakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class FakeRepo:
    def get_by_session_id(self, session_id, limit=None):
        return []

    def save(self, record):
        pass


def _ai(text):
    return AIMessage(content=text, usage_metadata={"input_tokens": 40, "output_tokens": 20, "total_tokens": 60})


def _service(monkeypatch, budget):
    monkeypatch.setattr(agent_service.AgentService, "__init__", lambda self, db: None)
    svc = agent_service.AgentService(None)
    svc._repo = FakeRepo()
    svc._agent = create_agent(
        model=FakeModel(responses=[_ai("uno"), _ai("dos"), _ai("tres")]),
        tools=[],
        middleware=[TokenBudgetMiddleware(budget=budget)],
    )
    agent_service._SESSION_TOKENS.clear()
    return svc


def test_acumula_entre_mensajes_y_corta(monkeypatch):
    svc = _service(monkeypatch, budget=100)
    r1 = asyncio.run(svc.chat("hola", "u", "s1"))
    r2 = asyncio.run(svc.chat("otra", "u", "s1"))
    assert agent_service._SESSION_TOKENS["s1"] == 120  # 60 + 60, no se reinicia
    r3 = asyncio.run(svc.chat("una más", "u", "s1"))
    assert (r1["answer"], r2["answer"]) == ("uno", "dos")
    assert r3["answer"] == BUDGET_EXCEEDED_RESPONSE


def test_otra_sesion_empieza_en_cero(monkeypatch):
    svc = _service(monkeypatch, budget=100)
    asyncio.run(svc.chat("hola", "u", "s1"))
    asyncio.run(svc.chat("otra", "u", "s1"))
    r = asyncio.run(svc.chat("hola", "u", "s2"))
    assert r["answer"] == "tres"
    assert agent_service._SESSION_TOKENS["s2"] == 60
