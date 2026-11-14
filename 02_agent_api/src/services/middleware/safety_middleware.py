"""SafetyGuardMiddleware — política de seguridad del asistente del instituto.

Hooks (node-style), ambos con @hook_config(can_jump_to=["end"]):
  - before_model → revisa el MENSAJE DEL USUARIO antes de gastar una llamada al modelo
  - after_model  → revisa la RESPUESTA DEL MODELO antes de entregarla

Cada política declara qué busca, dónde mira y qué hace:
  - "block":  reemplaza la respuesta por un mensaje seguro y corta el agente (jump_to="end")
  - "redact": enmascara el dato y deja seguir la respuesta

Son reglas deterministas y baratas (regex): no sustituyen a un clasificador con un
modelo, que llega en la parte 4. Sirven como primera barrera y dejan trazabilidad.
"""
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from src.utils.logger import get_logger

logger = get_logger(__name__)

SAFE_FALLBACK = (
    "Lo siento, no puedo ayudarte con esa consulta. "
    "Si tienes otra pregunta sobre el instituto, estaré encantado de ayudarte."
)


@dataclass(frozen=True)
class Policy:
    name: str
    where: Literal["input", "output"]
    action: Literal["block", "redact"]
    patterns: tuple[re.Pattern, ...]
    response: str = SAFE_FALLBACK        # mensaje al bloquear
    mask: str = "[dato oculto]"          # reemplazo al redactar


def _rx(*patterns: str) -> tuple[re.Pattern, ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# 1) ENTRADA: intentos de sacarle las instrucciones internas al asistente.
EXTRACCION_INSTRUCCIONES = Policy(
    name="extraccion_instrucciones",
    where="input",
    action="block",
    patterns=_rx(
        r"ignora\w*\s+(todas?\s+)?(tus|las|sus)\s+(instrucciones|reglas)",
        r"(system\s*prompt|prompt\s+(del\s+)?sistema|prompt\s+de\s+sistema)",
        r"(muestra|revela|dime|repite|copia)\w*\s+.{0,40}(tus|sus)\s+instrucciones\s+(internas|ocultas|iniciales|originales)",
    ),
    response=(
        "No puedo compartir ni modificar mis instrucciones internas. "
        "Puedo ayudarte con programas, horarios, costos y matrículas del instituto."
    ),
)

# 2) SALIDA: el asistente no debe prometer resultados ni condiciones comerciales.
PROMESAS_NO_AUTORIZADAS = Policy(
    name="promesas_no_autorizadas",
    where="output",
    action="block",
    patterns=_rx(
        r"\b(te|les?|nos)\s+(garantizo|aseguro|prometo|aseguramos|garantizamos)\b",
        r"\b(empleo|trabajo|certificaci[oó]n|aprobaci[oó]n)\s+(100\s?%\s+)?(garantizad[oa]|asegurad[oa])\b",
        r"\b100\s?%\s+garantizad[oa]\b",
    ),
    response=(
        "No puedo prometer resultados, descuentos ni condiciones especiales. "
        "Para eso, el equipo de admisiones te confirma lo vigente."
    ),
)

# 3) SALIDA: datos personales que no deben salir por WhatsApp (se enmascaran).
DATOS_PERSONALES = Policy(
    name="datos_personales",
    where="output",
    action="redact",
    patterns=_rx(
        r"[\w.+-]+@[\w-]+\.[\w.-]+",                          # correo
        r"(?<!\d)(?:\+?51[\s-]?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)",  # celular peruano
        r"(?<!\d)\d{13,16}(?!\d)",                            # tarjeta
        r"(?<!\d)\d{8}(?!\d)",                                # DNI
    ),
    mask="[dato oculto]",
)

DEFAULT_POLICIES: tuple[Policy, ...] = (
    EXTRACCION_INSTRUCCIONES,
    PROMESAS_NO_AUTORIZADAS,
    DATOS_PERSONALES,
)

LEAK_RESPONSE = (
    "No puedo compartir mis instrucciones internas. "
    "Puedo ayudarte con programas, horarios, costos y matrículas del instituto."
)


def _shingles(text: str, n: int = 8) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


class SafetyGuardMiddleware(AgentMiddleware):
    """Aplica las políticas de seguridad a la entrada y a la salida del agente.

    Args:
        policies: políticas a aplicar (por defecto DEFAULT_POLICIES).
        protected_texts: textos que nunca deben salir literalmente en una respuesta
            (por ejemplo, el system prompt). Se detecta por coincidencia de
            fragmentos de 8 palabras, no por la frase completa.
    """

    def __init__(
        self,
        policies: tuple[Policy, ...] | None = None,
        protected_texts: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.policies = tuple(DEFAULT_POLICIES if policies is None else policies)
        self._protected = set().union(*(_shingles(t) for t in (protected_texts or [])))

    # ── helpers ─────────────────────────────────────────────────────────────

    def _first_match(self, text: str, where: str, action: str) -> Policy | None:
        for policy in self.policies:
            if policy.where == where and policy.action == action:
                if any(p.search(text) for p in policy.patterns):
                    return policy
        return None

    def _leaks_protected(self, text: str) -> bool:
        return bool(self._protected) and bool(_shingles(text) & self._protected)

    def _check_input(self, state: AgentState) -> dict[str, Any] | None:
        last = state["messages"][-1]
        if not isinstance(last, HumanMessage):  # solo lo que escribe el usuario
            return None
        policy = self._first_match(str(last.content), "input", "block")
        if policy is None:
            return None
        logger.warning(
            "Mensaje bloqueado antes de llamar al modelo",
            extra={"middleware": "SafetyGuardMiddleware", "policy": policy.name, "where": "input"},
        )
        return {"messages": [AIMessage(content=policy.response)], "jump_to": "end"}

    def _check_output(self, state: AgentState) -> dict[str, Any] | None:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or last.tool_calls:  # una llamada a tool no es respuesta final
            return None
        text = last.content if isinstance(last.content, str) else str(last.content)

        if self._leaks_protected(text):
            logger.warning(
                "Respuesta bloqueada",
                extra={"middleware": "SafetyGuardMiddleware", "policy": "fuga_instrucciones", "where": "output"},
            )
            return {"messages": [AIMessage(content=LEAK_RESPONSE, id=last.id)], "jump_to": "end"}

        policy = self._first_match(text, "output", "block")
        if policy is not None:
            logger.warning(
                "Respuesta bloqueada",
                extra={"middleware": "SafetyGuardMiddleware", "policy": policy.name, "where": "output"},
            )
            return {"messages": [AIMessage(content=policy.response, id=last.id)], "jump_to": "end"}

        redacted, hits = text, []
        for policy in self.policies:
            if policy.where == "output" and policy.action == "redact":
                for pattern in policy.patterns:
                    redacted, n = pattern.subn(policy.mask, redacted)
                    if n:
                        hits.append(policy.name)
        if hits:
            logger.warning(
                "Respuesta con datos enmascarados",
                extra={"middleware": "SafetyGuardMiddleware", "policy": sorted(set(hits)), "where": "output"},
            )
            return {"messages": [AIMessage(content=redacted, id=last.id)]}  # sin jump: la respuesta sigue
        return None

    # ── hooks ───────────────────────────────────────────────────────────────

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_input(state)

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_input(state)

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_output(state)

    @hook_config(can_jump_to=["end"])
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._check_output(state)
