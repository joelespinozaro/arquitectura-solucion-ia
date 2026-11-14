import os
from pathlib import Path

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.chat import chat_router
from src.routes.errors import router as errors_router
from src.routes.feedback import router as feedback_router
from src.routes.evaluate import router as evaluate_router
from src.routes.scan import router as scan_router
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _root_cause(exc: BaseException) -> str:
    """Los errores de MCP llegan envueltos en un ExceptionGroup ("unhandled errors in a
    TaskGroup"). Se desenvuelve para mostrar la causa real (por ejemplo, un .env faltante)."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return f"{type(exc).__name__}: {exc}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: conectar a los MCP servers configurados y reinicializar el agente con
    todas las tools (y, si el demo MCP server expone skills como recursos MCP,
    con SkillMiddleware)."""
    from src.services.tools import (
        get_all_tools,
        load_demo_mcp_skills,
        load_demo_mcp_tools,
        load_neon_tools,
    )
    from src.services.agent_service import init_agent

    mcp_tools = []
    demo_client = None
    skills = []

    try:
        neon_tools, _ = await load_neon_tools()
        mcp_tools.extend(neon_tools)
        if neon_tools:
            logger.info("Neon MCP conectado — %d tool(s) disponibles", len(neon_tools))
    except Exception as exc:
        logger.warning("Error conectando a Neon MCP: %s. Continuando sin esas tools.", exc)

    try:
        demo_tools, demo_client = await load_demo_mcp_tools()
        mcp_tools.extend(demo_tools)
        if demo_tools:
            logger.info("Demo MCP server conectado — %d tool(s) disponibles", len(demo_tools))
    except Exception as exc:
        logger.warning(
            "Error conectando al demo MCP server: %s. Continuando sin esas tools. "
            "Revisa 03_mcp_server/.env, las dependencias de 03_mcp_server/requirements.txt y que DEMO_MCP_SERVER_PATH sea absoluta.",
            _root_cause(exc),
        )
        from src.services.tools import diagnose_demo_mcp_server

        causa = diagnose_demo_mcp_server()
        if causa:
            logger.warning("Causa probable del fallo del demo MCP server: %s", causa)

    try:
        skills = await load_demo_mcp_skills(demo_client)
        if skills:
            logger.info("Skills descubiertas en el demo MCP server: %s", [s["name"] for s in skills])
    except Exception as exc:
        logger.warning("Error descubriendo skills del demo MCP server: %s. Continuando sin skills.", exc)

    all_tools = get_all_tools(mcp_tools or None)
    init_agent(all_tools, demo_client, skills)
    logger.info("Registro de tools listo: %s", [t.name for t in all_tools])

    yield


app = FastAPI(
    title="Agente Simple",
    description="Asistente simple",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(errors_router)
app.include_router(feedback_router)
app.include_router(evaluate_router)
app.include_router(scan_router)

# Web chat (06_web_chat): si la carpeta existe (repo completo o WEB_CHAT_DIR), se sirve en /chat/
_web_dir = Path(os.getenv("WEB_CHAT_DIR") or Path(__file__).resolve().parents[2] / "06_web_chat")
if (_web_dir / "index.html").is_file():
    from fastapi.staticfiles import StaticFiles
    app.mount("/chat", StaticFiles(directory=_web_dir, html=True), name="web_chat")

if __name__ == "__main__":
    logger.info("Iniciando servidor en puerto 8080")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)
