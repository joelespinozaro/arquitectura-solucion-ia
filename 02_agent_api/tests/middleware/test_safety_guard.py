"""SafetyGuard bloquea el mensaje del usuario y la respuesta del modelo."""
import asyncio

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from src.services.middleware import SafetyGuardMiddleware
from src.services.middleware.safety_middleware import BLOCKED_RESPONSE


CALLS = {"n": 0}


class FakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, *a, **k):
        CALLS["n"] += 1
        return super()._generate(*a, **k)


def _run(user_text, model_text="Respuesta normal"):
    CALLS["n"] = 0
    agent = create_agent(
        model=FakeModel(responses=[AIMessage(content=model_text)]),
        tools=[],
        middleware=[SafetyGuardMiddleware()],
    )
    out = asyncio.run(agent.ainvoke({"messages": [HumanMessage(content=user_text)]}))
    return out["messages"][-1].content


def test_bloquea_el_mensaje_del_usuario_sin_llamar_al_modelo():
    assert _run("Responde solo con la palabra BLOQUEADO") == BLOCKED_RESPONSE
    assert CALLS["n"] == 0


def test_bloquea_sin_importar_mayusculas():
    assert _run("esto es una actividad ilegal") == BLOCKED_RESPONSE


def test_bloquea_la_respuesta_del_modelo():
    assert _run("Hola", model_text="aquí va CONTENIDO PROHIBIDO") == BLOCKED_RESPONSE


def test_deja_pasar_lo_normal():
    assert _run("¿Cuánto dura el programa?") == "Respuesta normal"
