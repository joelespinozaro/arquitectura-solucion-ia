"""SafetyGuardMiddleware — guardia de contenido con jump_to.

Hooks utilizados (node-style), ambos con @hook_config(can_jump_to=["end"]):
  - before_model → revisa el MENSAJE DEL USUARIO antes de gastar una llamada al modelo
  - after_model  → revisa la RESPUESTA DEL MODELO antes de entregarla

Si detecta un término prohibido corta la ejecución del agente (jump_to="end")
y devuelve una respuesta estándar.
"""
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Términos por defecto que activan el guard (case-insensitive)
DEFAULT_BLOCKED_TERMS: list[str] = [
    "BLOQUEADO",
    "CONTENIDO PROHIBIDO",
    "ACTIVIDAD ILEGAL",
]

BLOCKED_RESPONSE = (
    "Lo siento, no puedo ayudarte con esa consulta. "
    "Si tienes otra pregunta, estaré encantado de ayudarte."
)


class SafetyGuardMiddleware(AgentMiddleware):
    """Guardia de contenido que intercepta mensajes y respuestas con términos prohibidos.

    Si el mensaje del usuario o la respuesta del modelo contiene algún término
    bloqueado, devuelve la respuesta estándar y detiene la ejecución del agente
    inmediatamente (jump_to='end').

    Args:
        blocked_terms: lista de términos prohibidos (case-insensitive).
                       Si no se pasa, usa DEFAULT_BLOCKED_TERMS.
    """

    def __init__(self, blocked_terms: list[str] | None = None) -> None:
        super().__init__()
        self.blocked_terms = [
            t.upper() for t in (blocked_terms or DEFAULT_BLOCKED_TERMS)
        ]

    def _find_term(self, content: Any) -> str | None:
        text = str(content).upper()
        return next((t for t in self.blocked_terms if t in text), None)

    def _check_input(self, state: AgentState) -> dict[str, Any] | None:
        last = state["messages"][-1]
        if not isinstance(last, HumanMessage):  # solo la entrada del usuario, no los resultados de tools
            return None
        term = self._find_term(last.content)
        if term is None:
            return None
        logger.warning(
            "Mensaje bloqueado antes de llamar al modelo",
            extra={"middleware": "SafetyGuardMiddleware", "blocked_term": term, "where": "input"},
        )
        return {"messages": [AIMessage(content=BLOCKED_RESPONSE)], "jump_to": "end"}

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_input(state)

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_input(state)

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_message = state["messages"][-1]
        content = str(getattr(last_message, "content", "")).upper()

        for term in self.blocked_terms:
            if term in content:
                logger.warning(
                    "Contenido bloqueado detectado",
                    extra={"middleware": "SafetyGuardMiddleware", "blocked_term": term},
                )
                return {
                    "messages": [AIMessage(content=BLOCKED_RESPONSE)],
                    "jump_to": "end",
                }

        return None  # flujo normal

    # ── Versión ASYNC ───────────────────────────────────────────────────────

    @hook_config(can_jump_to=["end"])
    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        last_message = state["messages"][-1]
        content = str(getattr(last_message, "content", "")).upper()

        for term in self.blocked_terms:
            if term in content:
                logger.warning(
                    "Contenido bloqueado detectado (async)",
                    extra={"middleware": "SafetyGuardMiddleware", "blocked_term": term},
                )
                return {
                    "messages": [AIMessage(content=BLOCKED_RESPONSE)],
                    "jump_to": "end",
                }

        return None
