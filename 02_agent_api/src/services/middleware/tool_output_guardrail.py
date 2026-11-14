"""ToolOutputGuardrail: revisa lo que devuelve cada tool antes de que lo lea el modelo.

Cubre la inyección indirecta (instrucciones escondidas en el resultado de una
tool o en un documento recuperado) y la fuga de secretos. Usa las mismas reglas
que `/v1/scan/input` (`security_scan_service`), con PII en `off` porque los datos
que devuelven las tools del instituto ya vienen minimizados.

Si el resultado se bloquea, el modelo recibe un aviso neutro en lugar del
contenido, así no puede seguir las instrucciones que traía.
"""
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from src.services import security_scan_service as scan
from src.utils.logger import get_logger

logger = get_logger(__name__)

BLOCKED_NOTICE = (
    "[El resultado de la herramienta fue bloqueado por seguridad porque contenía "
    "instrucciones o datos que no deben llegar al asistente. Informa a la persona "
    "que no pudiste completar la consulta.]"
)


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in content
        )
    return str(content)


def _review(result: Any, tool_name: str) -> Any:
    if not isinstance(result, ToolMessage):
        return result
    text = _text_of(result.content)
    if not text:
        return result
    verdict = scan.scan_input(text, pii_mode="off")
    if verdict.decision != "block":
        return result
    logger.warning(
        "tool_output_bloqueado herramienta=%s findings=%s audit_id=%s",
        tool_name,
        [f"{f.layer}:{f.category}" for f in verdict.findings],
        verdict.audit_id,
    )
    return ToolMessage(
        content=BLOCKED_NOTICE,
        tool_call_id=result.tool_call_id,
        name=result.name,
        status="error",
    )


class ToolOutputGuardrail(AgentMiddleware):
    def wrap_tool_call(self, request, handler):
        return _review(handler(request), request.tool_call.get("name", ""))

    async def awrap_tool_call(self, request, handler):
        return _review(await handler(request), request.tool_call.get("name", ""))
