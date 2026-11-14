"""Chat por SSE: eventos en vivo del agente (skill, tool, done) con un modelo falso."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src.routes import chat as chat_route
from src.services import agent_service


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@tool
def load_skill(skill_name: str) -> str:
    """Carga una skill."""
    return f"guia de {skill_name}"


@tool
def estado_matricula(dni: str) -> str:
    """Estado de matricula."""
    return "Matriculado en Data Engineer"


class FakeRepo:
    def __init__(self):
        self.saved = []

    def get_by_session_id(self, session_id, limit=None):
        return []

    def save(self, record):
        self.saved.append(record)


def build_agent(responses):
    return create_agent(model=FakeToolModel(responses=responses), tools=[load_skill, estado_matricula])


@pytest.fixture
def repo(monkeypatch):
    r = FakeRepo()
    state = {"agent": None}

    def fake_init(self, db):
        self._repo = r
        self._agent = state["agent"]  # ramas donde el agente es atributo de instancia (partes 1 a 3)

    monkeypatch.setattr(agent_service.AgentService, "__init__", fake_init)
    r.state = state
    return r


@pytest.fixture
def client(monkeypatch, repo):
    class DummyDb:
        def close(self):
            pass

    monkeypatch.setattr(chat_route, "SessionLocal", lambda: DummyDb())
    app = FastAPI()
    app.include_router(chat_route.chat_router)
    return TestClient(app)


def use_agent(monkeypatch, repo, agent):
    repo.state["agent"] = agent
    monkeypatch.setattr(agent_service, "_agent", agent, raising=False)  # ramas con agente a nivel de módulo


def parse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(l.split(": ", 1) for l in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_stream_emite_skill_tool_y_done(client, repo, monkeypatch):
    use_agent(monkeypatch, repo, build_agent([
        AIMessage(content="", tool_calls=[{"name": "load_skill", "args": {"skill_name": "matricula_y_asesoria"}, "id": "c1"}]),
        AIMessage(content="", tool_calls=[{"name": "estado_matricula", "args": {"dni": "90000001"}, "id": "c2"}]),
        AIMessage(content="Estás matriculada en Data Engineer."),
    ]))
    r = client.post("/api/chat/stream", json={"question": "mi matricula", "user": "joel"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse(r.text)
    kinds = [k for k, _ in events]
    assert kinds[0] == "session"
    assert kinds.index("skill") < kinds.index("tool_start") < len(kinds) - 1 - kinds[::-1].index("tool_end")
    assert kinds[-1] == "done"
    done = events[-1][1]
    assert done["answer"] == "Estás matriculada en Data Engineer."
    assert done["session_id"] == events[0][1]["session_id"]
    skill = next(d for k, d in events if k == "skill")
    assert skill["name"] == "matricula_y_asesoria"
    tool_start = next(d for k, d in events if k == "tool_start")
    assert tool_start["tool"] == "estado_matricula" and tool_start["label"]
    assert "sources" in done
    assert len(repo.saved) == 1 and repo.saved[0].question == "mi matricula"


def test_stream_error_se_informa_como_evento(client, repo, monkeypatch):
    class Boom:
        async def astream(self, *a, **k):
            raise RuntimeError("falla interna con detalle sensible")
            yield  # pragma: no cover

    use_agent(monkeypatch, repo, Boom())
    events = parse(client.post("/api/chat/stream", json={"question": "hola", "user": "joel"}).text)
    assert events[-1][0] == "error"
    assert "sensible" not in json.dumps(events[-1][1])


def test_stream_con_bloqueo_de_guardrail_que_devuelve_dict(client, repo, monkeypatch):
    """Los guardrails devuelven el bloqueo como dict ({"role": ..., "content": ...}): el stream no debe romperse."""
    from langchain.agents.middleware import AgentMiddleware, hook_config

    class Bloqueo(AgentMiddleware):
        @hook_config(can_jump_to=["end"])
        async def abefore_model(self, state, runtime):
            return {"messages": [{"role": "assistant", "content": "Mensaje bloqueado por seguridad"}], "jump_to": "end"}

    agente = create_agent(model=FakeToolModel(responses=[AIMessage(content="no debería llegar")]),
                          tools=[], middleware=[Bloqueo()])
    use_agent(monkeypatch, repo, agente)
    events = parse(client.post("/api/chat/stream", json={"question": "ataque", "user": "joel"}).text)
    assert events[-1][0] == "done"
    assert events[-1][1]["answer"] == "Mensaje bloqueado por seguridad"
