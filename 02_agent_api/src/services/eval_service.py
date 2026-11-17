"""Evaluación sobre tráfico real (M5S2 parte 2).

Dos piezas, ambas pensadas para correr como script y para testearse sin red:

  - juzgar_conversaciones: un modelo (LLM-as-judge) lee cada conversación reciente y
    decide si la respuesta se apoya en la información disponible o se la inventó.
    El resultado se adjunta a la traza de LangSmith como feedback `grounded`.
  - pasar_negativos_a_dataset: las conversaciones que el usuario marcó con pulgar
    abajo se guardan como casos de un dataset de LangSmith. Un error de producción
    se convierte en un caso de prueba.
"""
import json
import re
from typing import Any, Callable, Dict, List, Optional

from src.repositories.models.history import History
from src.utils.logger import get_logger
from src.utils.observability import enviar_feedback, obtener_cliente

logger = get_logger(__name__)

CLAVE_JUEZ = "grounded"
DATASET_ERRORES = "instituto-errores-produccion"

PROMPT_JUEZ = """Eres un evaluador estricto de un asistente de un instituto de tecnología.
Recibes la PREGUNTA, la RESPUESTA del asistente y el CONTEXTO que el asistente tenía
(documentos y datos que devolvieron sus herramientas).

Puntúa con 1 si la respuesta se apoya en el contexto o es una orientación general
razonable que no afirma datos concretos. Puntúa con 0 si afirma datos concretos
(precios, fechas, requisitos, nombres, cifras) que NO están en el contexto, o si
promete algo que el instituto no ha confirmado.

Responde SOLO con un JSON: {"score": 0 o 1, "razon": "una frase corta"}

PREGUNTA: {pregunta}
CONTEXTO: {contexto}
RESPUESTA: {respuesta}"""


def contexto_de(sources_json: Optional[str]) -> str:
    """Junta en texto lo que las tools devolvieron en esa conversación."""
    if not sources_json:
        return "(sin contexto: el asistente no usó herramientas)"
    try:
        fuentes = json.loads(sources_json)
    except (TypeError, ValueError):
        return "(sin contexto legible)"
    trozos: List[str] = []
    for f in fuentes if isinstance(fuentes, list) else []:
        trozos.extend(str(c) for c in (f.get("contexts") or []))
        for campo in f.get("fields") or []:
            trozos.append(f"{campo.get('label')}: {campo.get('value')}")
        if f.get("content"):
            trozos.append(str(f["content"]))
    return "\n".join(trozos) or "(sin contexto: el asistente no usó herramientas)"


def parsear_veredicto(texto: str) -> Optional[Dict[str, Any]]:
    """Extrae {"score", "razon"} de la respuesta del juez. None si no se entiende."""
    m = re.search(r"\{.*\}", texto, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        score = float(data["score"])
    except (ValueError, KeyError, TypeError):
        return None
    if score not in (0.0, 1.0):
        return None
    return {"score": score, "razon": str(data.get("razon", ""))[:300]}


def juzgar(llm: Any, h: History) -> Optional[Dict[str, Any]]:
    prompt = (
        PROMPT_JUEZ.replace("{pregunta}", h.question)
        .replace("{contexto}", contexto_de(h.sources))
        .replace("{respuesta}", h.answer)
    )
    # La llamada del juez no debe aparecer como una conversación más en LangSmith
    from langsmith import tracing_context

    with tracing_context(enabled=False):
        salida = llm.invoke(prompt)
    return parsear_veredicto(getattr(salida, "content", str(salida)))


def juzgar_conversaciones(
    llm: Any,
    historial: List[History],
    enviar: Callable[..., bool] = enviar_feedback,
) -> Dict[str, Any]:
    """Juzga cada conversación y adjunta `grounded` a su traza."""
    resumen = {"juzgadas": 0, "ok": 0, "inventadas": 0, "sin_veredicto": 0, "no_enviadas": 0, "detalle": []}
    for h in historial:
        veredicto = juzgar(llm, h)
        if veredicto is None:
            resumen["sin_veredicto"] += 1
            continue
        resumen["juzgadas"] += 1
        resumen["ok" if veredicto["score"] == 1.0 else "inventadas"] += 1
        if not enviar(str(h.trace_id), CLAVE_JUEZ, veredicto["score"], veredicto["razon"]):
            resumen["no_enviadas"] += 1
        resumen["detalle"].append((str(h.trace_id), veredicto["score"], veredicto["razon"]))
    return resumen


def pasar_negativos_a_dataset(
    historial: List[History],
    nombre: str = DATASET_ERRORES,
    cliente: Any = None,
) -> int:
    """Guarda las conversaciones con pulgar abajo como ejemplos de un dataset."""
    cliente = cliente or obtener_cliente()
    if cliente is None:
        raise RuntimeError("LangSmith no está configurado (LANGSMITH_TRACING y LANGSMITH_API_KEY).")
    if not historial:
        return 0
    if not cliente.has_dataset(dataset_name=nombre):
        cliente.create_dataset(nombre, description="Respuestas que un usuario marcó como malas en producción")
    ejemplos = [
        {
            "inputs": {"question": h.question},
            "outputs": {"respuesta_mala": h.answer},
            "metadata": {
                "trace_id": str(h.trace_id),
                "error_type_id": h.error_type_id,
                "observaciones": h.observations,
            },
        }
        for h in historial
    ]
    cliente.create_examples(dataset_name=nombre, examples=ejemplos)
    return len(ejemplos)
