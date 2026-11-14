"""OutputGuardrail: revisa la respuesta final del modelo antes de entregarla.

Usa las mismas reglas que `/v1/scan/output`:
- canary token del system prompt (fuga del prompt) -> bloquea
- secretos o credenciales -> bloquea
- PII según `OUTPUT_PII_MODE` (block | mask | off)

Solo revisa respuestas finales (sin tool_calls pendientes).
"""
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime

from src.services import security_scan_service as scan
from src.utils.environment import CANARY_TOKEN, OUTPUT_PII_MODE
from src.utils.logger import get_logger

logger = get_logger(__name__)

BLOCKED_RESPONSE = (
    "No puedo compartir esa información. Si tienes otra consulta sobre "
    "nuestros programas, con gusto te ayudo."
)


class OutputGuardrail(AgentMiddleware):
    def __init__(self, pii_mode: str = OUTPUT_PII_MODE, canary_token: str = CANARY_TOKEN) -> None:
        super().__init__()
        self.pii_mode = pii_mode
        self.canary_token = canary_token

    def _review(self, state: AgentState) -> dict[str, Any] | None:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or getattr(last, "tool_calls", None):
            return None
        text = last.content if isinstance(last.content, str) else ""
        if not text:
            return None
        verdict = scan.scan_output(text, self.pii_mode, [self.canary_token])
        if verdict.decision == "allow":
            return None
        logger.warning(
            "salida_%s findings=%s audit_id=%s",
            verdict.decision,
            [f"{f.layer}:{f.category}" for f in verdict.findings],
            verdict.audit_id,
        )
        if verdict.decision == "block":
            return {"messages": [AIMessage(content=BLOCKED_RESPONSE, id=last.id)], "jump_to": "end"}
        return {"messages": [AIMessage(content=verdict.text, id=last.id)]}

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._review(state)

    @hook_config(can_jump_to=["end"])
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self._review(state)
