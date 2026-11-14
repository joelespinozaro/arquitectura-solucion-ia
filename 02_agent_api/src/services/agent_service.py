import json
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypedDict
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from src.services.middleware import (
    LoggingMiddleware,
    RetryMiddleware,
    SafetyGuardMiddleware,
    TokenBudgetMiddleware,
)
from src.services.tools import get_weather, retrieve_documents
from src.repositories.history_repository import HistoryRepository
from src.repositories.models.history import History
from src.utils.environment import (
    HISTORY_LIMIT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    TOKEN_BUDGET,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "Eres un asistente útil y amigable. Responde siempre en español. "
    "Sé conciso en tus respuestas. "
    "SIEMPRE que la pregunta trate sobre la academia, sus programas, cursos, "
    "temarios, precios, duración, requisitos, certificaciones o cualquier "
    "información institucional, DEBES usar la herramienta retrieve_documents "
    "para consultar la base de conocimiento antes de responder; no respondas "
    "esos temas de memoria. Si la herramienta no encuentra información "
    "relevante, dilo explícitamente en tu respuesta. "
    "SIEMPRE que el usuario pida una ruta de aprendizaje, progresión de nivel, "
    "prerrequisitos o cómo avanzar dentro de un área académica específica "
    "(por ejemplo desarrollo de software, data science e IA, diseño UX/UI o "
    "ciberseguridad), DEBES usar la herramienta load_skill para cargar la "
    "guía detallada de esa área antes de responder."
)

RETRIEVER_TOOL_NAME = "retrieve_documents"


class Skill(TypedDict):
    """Una skill que se puede revelar progresivamente al agente (progressive disclosure)."""

    name: str  # Identificador único de la skill
    description: str  # 1-2 frases mostradas siempre en el system prompt
    content: str  # Contenido completo con instrucciones detalladas


SKILLS: List[Skill] = [
    {
        "name": "desarrollo_software",
        "description": (
            "Ruta de aprendizaje, prerrequisitos y progresión de nivel para el "
            "área de Desarrollo de Software (backend, frontend y full-stack)."
        ),
        "content": (
            "# Ruta de aprendizaje: Desarrollo de Software\n\n"
            "## Niveles\n"
            "1. **Básico**: lógica de programación, fundamentos de un lenguaje "
            "(Python o JavaScript), control de versiones con Git.\n"
            "2. **Intermedio**: estructuras de datos, POO, bases de datos "
            "relacionales (SQL), APIs REST con un framework (Django/FastAPI o "
            "Express/NestJS).\n"
            "3. **Avanzado**: arquitectura de software, testing automatizado, "
            "contenedores (Docker), CI/CD, sistemas distribuidos.\n\n"
            "## Prerrequisitos\n"
            "- Para cursar Intermedio se requiere aprobar el módulo Básico o "
            "acreditar experiencia equivalente.\n"
            "- Para cursar Avanzado se requiere haber completado al menos un "
            "proyecto final del nivel Intermedio.\n\n"
            "## Especializaciones sugeridas al finalizar\n"
            "- Backend (APIs, microservicios)\n"
            "- Frontend (React/Vue)\n"
            "- Full-stack\n\n"
            "## Recomendación de progresión\n"
            "Se recomienda no saltar niveles: cada nivel construye las bases "
            "necesarias para el siguiente, especialmente en fundamentos de "
            "programación y bases de datos."
        ),
    },
    {
        "name": "data_science_ia",
        "description": (
            "Ruta de aprendizaje, prerrequisitos y progresión de nivel para el "
            "área de Data Science e Inteligencia Artificial."
        ),
        "content": (
            "# Ruta de aprendizaje: Data Science & IA\n\n"
            "## Niveles\n"
            "1. **Básico**: fundamentos de estadística y probabilidad, Python "
            "para análisis de datos (pandas, numpy), visualización de datos.\n"
            "2. **Intermedio**: machine learning supervisado y no supervisado, "
            "feature engineering, evaluación de modelos.\n"
            "3. **Avanzado**: deep learning (redes neuronales), procesamiento "
            "de lenguaje natural, sistemas de IA generativa (LLMs, RAG).\n\n"
            "## Prerrequisitos\n"
            "- Se recomienda base de matemáticas (álgebra lineal, cálculo "
            "básico) antes de iniciar el nivel Intermedio.\n"
            "- El nivel Avanzado requiere haber aprobado machine learning "
            "supervisado del nivel Intermedio.\n\n"
            "## Especializaciones sugeridas al finalizar\n"
            "- Machine Learning Engineer\n"
            "- Data Analyst\n"
            "- Ingeniero de IA Generativa\n\n"
            "## Recomendación de progresión\n"
            "Reforzar estadística y Python antes de avanzar a modelos "
            "complejos; los proyectos prácticos con datasets reales son clave "
            "en cada nivel."
        ),
    },
    {
        "name": "diseno_ux_ui",
        "description": (
            "Ruta de aprendizaje, prerrequisitos y progresión de nivel para el "
            "área de Diseño UX/UI."
        ),
        "content": (
            "# Ruta de aprendizaje: Diseño UX/UI\n\n"
            "## Niveles\n"
            "1. **Básico**: fundamentos de diseño (color, tipografía, "
            "composición), principios de usabilidad.\n"
            "2. **Intermedio**: investigación de usuarios (research), "
            "arquitectura de información, wireframing y prototipado "
            "(Figma).\n"
            "3. **Avanzado**: design systems, testing de usabilidad, diseño "
            "de interacción avanzado, handoff con equipos de desarrollo.\n\n"
            "## Prerrequisitos\n"
            "- El nivel Intermedio requiere manejo básico de herramientas de "
            "diseño (Figma o similar).\n"
            "- El nivel Avanzado requiere haber presentado al menos un "
            "prototipo evaluado en el nivel Intermedio.\n\n"
            "## Especializaciones sugeridas al finalizar\n"
            "- UX Researcher\n"
            "- UI/Product Designer\n\n"
            "## Recomendación de progresión\n"
            "Priorizar práctica con research real y prototipado antes de "
            "profundizar en design systems, para no diseñar sin validar con "
            "usuarios."
        ),
    },
    {
        "name": "ciberseguridad",
        "description": (
            "Ruta de aprendizaje, prerrequisitos y progresión de nivel para el "
            "área de Ciberseguridad."
        ),
        "content": (
            "# Ruta de aprendizaje: Ciberseguridad\n\n"
            "## Niveles\n"
            "1. **Básico**: fundamentos de redes, sistemas operativos "
            "(Linux), conceptos de seguridad de la información.\n"
            "2. **Intermedio**: hacking ético (pentesting), análisis de "
            "vulnerabilidades, hardening de sistemas.\n"
            "3. **Avanzado**: respuesta a incidentes, forense digital, "
            "preparación para certificaciones (CEH, OSCP).\n\n"
            "## Prerrequisitos\n"
            "- El nivel Intermedio requiere fundamentos sólidos de redes y "
            "Linux del nivel Básico.\n"
            "- El nivel Avanzado requiere haber completado laboratorios de "
            "pentesting del nivel Intermedio.\n\n"
            "## Especializaciones sugeridas al finalizar\n"
            "- Analista SOC\n"
            "- Pentester / Red Team\n\n"
            "## Recomendación de progresión\n"
            "Es indispensable dominar redes y sistemas operativos antes de "
            "avanzar a hacking ético; se recomienda práctica constante en "
            "laboratorios (labs) controlados."
        ),
    },
]


@tool
def load_skill(skill_name: str) -> str:
    """Carga el contenido completo de una skill de orientación curricular en el
    contexto del agente. Úsala cuando el usuario pida una ruta de aprendizaje,
    prerrequisitos o progresión de nivel dentro de un área académica específica.

    Args:
        skill_name: nombre de la skill a cargar (ej. "desarrollo_software",
            "data_science_ia", "diseno_ux_ui", "ciberseguridad").
    """
    logger.info("load_skill: el modelo pidió la skill %s", skill_name)
    for skill in SKILLS:
        if skill["name"] == skill_name:
            return f"Skill cargada: {skill_name}\n\n{skill['content']}"

    available = ", ".join(s["name"] for s in SKILLS)
    return f"Skill '{skill_name}' no encontrada. Skills disponibles: {available}"


class SkillMiddleware(AgentMiddleware):
    """Middleware que inyecta las descripciones de las skills en el system prompt
    y expone la tool load_skill para cargarlas on-demand (progressive disclosure)."""

    tools = [load_skill]

    def __init__(self) -> None:
        skills_list = [f"- **{skill['name']}**: {skill['description']}" for skill in SKILLS]
        self.skills_prompt = "\n".join(skills_list)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        skills_addendum = (
            f"\n\n## Skills disponibles\n\n{self.skills_prompt}\n\n"
            "Usa la herramienta load_skill cuando necesites la guía detallada "
            "de una de estas áreas académicas."
        )
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        skills_addendum = (
            f"\n\n## Skills disponibles\n\n{self.skills_prompt}\n\n"
            "Usa la herramienta load_skill cuando necesites la guía detallada "
            "de una de estas áreas académicas."
        )
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return await handler(modified_request)


# Tokens acumulados por sesión. Vive en memoria del proceso (AgentService se crea por
# petición, así que el contador no puede ser un atributo de instancia). Se pierde si
# reinicias el API. En producción iría a Redis o a la base de datos.
_SESSION_TOKENS: Dict[str, int] = {}


class AgentService:
    def __init__(self, db: Session) -> None:
        self._repo = HistoryRepository(db)
        self._llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY)
        self._agent = create_agent(
            model=self._llm,
            tools=[get_weather, retrieve_documents],
            system_prompt=SYSTEM_PROMPT,
            middleware=[
                LoggingMiddleware(),                      # 1° logging granular de cada LLM call
                TokenBudgetMiddleware(budget=TOKEN_BUDGET), # 2° control de presupuesto de tokens
                SafetyGuardMiddleware(),                  # 3° guardia de contenido prohibido
                RetryMiddleware(max_retries=3),           # 4° reintentos ante errores transitorios
                SkillMiddleware(),                        # 5° inyección de skills (progressive disclosure)
            ],
        )

    async def chat(self, question: str, user: str, session_id: Optional[str]) -> dict:
        logger.info(f"Pregunta entrante de {user}: {question}")

        is_new_session = not session_id
        if is_new_session:
            logger.info("Creando nueva sesión")
            session_id = str(uuid.uuid4())

        trace_id = str(uuid.uuid4())

        logger.info(
            "Iniciando chat",
            extra={"session_id": session_id, "trace_id": trace_id, "user": user},
        )

        t0 = time.perf_counter()
        history_records = [] if is_new_session else self._repo.get_by_session_id(session_id, limit=HISTORY_LIMIT)
        t_history = time.perf_counter() - t0

        history_messages: List[BaseMessage] = []
        for record in history_records:
            history_messages.append(HumanMessage(content=record.question))
            history_messages.append(AIMessage(content=record.answer))

        t0 = time.perf_counter()
        tokens_before = _SESSION_TOKENS.get(session_id, 0)
        agent_response = await self._agent.ainvoke(
            {
                "messages": [*history_messages, HumanMessage(content=question)],
                "token_count": tokens_before,  # el presupuesto sigue corriendo entre mensajes
            }
        )
        _SESSION_TOKENS[session_id] = agent_response.get("token_count", tokens_before)
        logger.info(
            "Presupuesto de la sesión",
            extra={"session_id": session_id, "tokens_sesion": _SESSION_TOKENS[session_id], "budget": TOKEN_BUDGET},
        )
        result = self._parse_agent_response(agent_response)
        retrieved_contexts = self._extract_retrieved_contexts(agent_response)
        t_agent = time.perf_counter() - t0

        t0 = time.perf_counter()
        self._repo.save(
            History(
                trace_id=trace_id,
                session_id=session_id,
                question=question,
                answer=result["answer"],
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                user=user,
                retrieved_contexts=(
                    json.dumps(retrieved_contexts, ensure_ascii=False)
                    if retrieved_contexts
                    else None
                ),
            )
        )
        t_save = time.perf_counter() - t0

        logger.info(
            "Chat finalizado",
            extra={
                "trace_id": trace_id,
                "session_id": session_id,
                "t_history_ms": round(t_history * 1000, 2),
                "t_agent_ms": round(t_agent * 1000, 2),
                "t_save_ms": round(t_save * 1000, 2),
                "retrieved_contexts_count": len(retrieved_contexts or []),
            },
        )

        logger.info(f"Respuesta a la pregunta: {result['answer']}")

        return {
            "user": user,
            "answer": result["answer"],
            "session_id": session_id,
            "trace_id": trace_id,
        }

    async def chat_stream(self, question: str, user: str, session_id: Optional[str]):
        """Igual que chat(), pero emite eventos mientras el agente trabaja (SSE).

        Eventos: session, skill, tool_start, tool_end, done, error.
        La respuesta NO se emite token a token: se entrega completa en `done`,
        después de que OutputGuardrail y SafetyGuard pudieron revisarla. Streamear
        tokens crudos dejaría salir un secreto o el canary antes del filtro."""
        is_new_session = not session_id
        session_id = session_id or str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        yield {"type": "session", "session_id": session_id, "trace_id": trace_id}

        history_records = [] if is_new_session else self._repo.get_by_session_id(session_id, limit=HISTORY_LIMIT)
        history_messages: List[BaseMessage] = []
        for record in history_records:
            history_messages.append(HumanMessage(content=record.question))
            history_messages.append(AIMessage(content=record.answer))

        t0 = time.perf_counter()
        seen_calls: set = set()
        collected: Dict[str, BaseMessage] = {}   # id -> mensaje (una réplica posterior reemplaza a la anterior)
        order: List[str] = []
        try:
            tokens_before = _SESSION_TOKENS.get(session_id, 0)
            async for chunk in self._agent.astream(
                {"messages": [*history_messages, HumanMessage(content=question)],
                 "token_count": tokens_before},
                stream_mode="updates",
            ):
                for update in chunk.values():
                    if isinstance(update, dict) and "token_count" in update:
                        _SESSION_TOKENS[session_id] = update["token_count"]
                    for message in (update or {}).get("messages", []) if isinstance(update, dict) else []:
                        mid = getattr(message, "id", None) or f"anon-{len(order)}"
                        if mid not in collected:
                            order.append(mid)
                        collected[mid] = message
                        if isinstance(message, AIMessage):
                            for call in message.tool_calls or []:
                                if call["id"] in seen_calls:
                                    continue
                                seen_calls.add(call["id"])
                                if call["name"] == "load_skill":
                                    yield {"type": "skill", "id": call["id"],
                                           "name": (call.get("args") or {}).get("skill_name", "")}
                                else:
                                    yield {"type": "tool_start", "id": call["id"], "tool": call["name"],
                                           "label": call["name"], "input": call.get("args")}
                        elif isinstance(message, ToolMessage):
                            yield {"type": "tool_end", "id": message.tool_call_id, "tool": message.name or "tool",
                                   "ok": getattr(message, "status", "success") != "error"}
        except Exception as exc:  # el stream ya empezó: se informa como evento, no como 500
            logger.exception("Error en chat_stream")
            yield {"type": "error", "message": "No pude completar la respuesta. Intenta de nuevo."}
            return

        agent_response = {"messages": [collected[i] for i in order]}
        result = self._parse_agent_response(agent_response)
        answer = str(result["answer"])
        sources, files = [], []
        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        self._repo.save(
            History(
                trace_id=trace_id, session_id=session_id, question=question, answer=answer,
                input_tokens=result["input_tokens"], output_tokens=result["output_tokens"], user=user,
            )
        )
        logger.info("Chat stream finalizado", extra={"trace_id": trace_id, "session_id": session_id,
                                                    "t_agent_ms": elapsed_ms, "sources_count": len(sources)})
        yield {"type": "done", "answer": answer, "session_id": session_id, "trace_id": trace_id,
               "sources": sources, "files": files, "elapsed_ms": elapsed_ms,
               "input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}

    @staticmethod
    def _extract_retrieved_contexts(agent_response: dict) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for message in agent_response.get("messages", []):
            if isinstance(message, ToolMessage) and message.name == RETRIEVER_TOOL_NAME:
                artifact = getattr(message, "artifact", None)
                if artifact:
                    contexts.extend(artifact)
        return contexts

    @staticmethod
    def _parse_agent_response(agent_response: dict) -> dict:
        messages = agent_response.get("messages", [])
        answer = messages[-1].content if messages else ""

        input_tokens = 0
        output_tokens = 0
        for message in messages:
            usage = getattr(message, "usage_metadata", None)
            if usage:
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)

        return {
            "answer": answer,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }