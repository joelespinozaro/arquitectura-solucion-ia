"""Observabilidad con LangSmith (M5S2).

Reglas de este módulo:
  1. Si LangSmith no está configurado, todo es un no-op: el agente funciona igual.
  2. Si LangSmith falla (red, key vencida), se registra un warning y se sigue.
     La observabilidad NUNCA tumba la app.

LangChain/LangGraph ya trazan solos cuando existen LANGSMITH_TRACING y
LANGSMITH_API_KEY (environment.py las propaga a os.environ). Aquí solo se agrega
lo que convierte esa traza en algo útil:
  - el `trace_id` de la tabla `history` ES el id de la traza en LangSmith,
  - tags y metadata (sesión, usuario) para filtrar,
  - anotaciones (por ejemplo, qué capa de guardrail bloqueó).
"""
import os
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


def langsmith_activo() -> bool:
    """True si hay tracing configurado en este proceso."""
    return (
        os.getenv("LANGSMITH_TRACING", "").lower() == "true"
        and bool(os.getenv("LANGSMITH_API_KEY"))
    )


def trace_config(
    trace_id: str,
    session_id: str,
    user: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Config de LangChain para una invocación del agente.

    `run_id` fija el id de la traza raíz: así la fila de `history` y la traza de
    LangSmith comparten identificador. Es inofensivo si el tracing está apagado.
    """
    import uuid

    return {
        "run_id": uuid.UUID(trace_id),
        "run_name": "chat",
        "tags": ["instituto", *(tags or [])],
        "metadata": {"session_id": session_id, "user": user},
    }


def anotar_traza(**metadata: Any) -> None:
    """Agrega metadata al paso (run) que se está ejecutando, si hay traza activa."""
    if not langsmith_activo():
        return
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.add_metadata(metadata)
    except Exception as exc:  # nunca romper el flujo por observabilidad
        logger.warning("No pude anotar la traza en LangSmith: %s", exc)


# ── Feedback y datasets (M5S2 parte 2) ──────────────────────────────────────

_cliente = None
_session_id_cache: Dict[str, Any] = {}


def obtener_cliente():
    """Cliente de LangSmith (uno solo por proceso). None si no está configurado."""
    global _cliente
    if not langsmith_activo():
        return None
    if _cliente is None:
        from langsmith import Client

        _cliente = Client()
    return _cliente


def _project_session_id(client) -> Any:
    """UUID del proyecto de LangSmith. El SDK actual lo exige al crear feedback."""
    nombre = os.getenv("LANGSMITH_PROJECT", "default")
    if nombre not in _session_id_cache:
        _session_id_cache[nombre] = client.read_project(project_name=nombre).id
    return _session_id_cache[nombre]


def enviar_feedback(
    trace_id: str,
    key: str,
    score: Optional[float] = None,
    comment: Optional[str] = None,
) -> bool:
    """Adjunta un puntaje a la traza `trace_id`. Devuelve True si se envió.

    Nunca lanza: si LangSmith no está configurado o falla, devuelve False.
    """
    client = obtener_cliente()
    if client is None:
        return False
    try:
        import uuid

        run_id = uuid.UUID(str(trace_id))
        client.create_feedback(
            run_id=run_id,
            trace_id=run_id,
            key=key,
            score=score,
            comment=comment,
            session_id=_project_session_id(client),
        )
        return True
    except Exception as exc:
        logger.warning("No pude enviar feedback '%s' a LangSmith: %s", key, exc)
        return False
