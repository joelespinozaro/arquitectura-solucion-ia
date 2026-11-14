from typing import Dict, List, Tuple

from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.utils.environment import DEMO_MCP_SERVER_URL, NEON_API_KEY
from src.utils.gcp_auth import GoogleIDTokenAuth, cloud_run_audience
from src.utils.logger import get_logger

logger = get_logger(__name__)


@tool
def get_weather(location: str) -> str:
    """Devuelve el pronóstico del clima actual para la ubicación indicada."""
    return f"El clima en {location} es soleado con una temperatura de 22°C."


LOCAL_TOOLS = [get_weather]


async def load_neon_tools() -> Tuple[list, object | None]:
    """Conecta al MCP de Neon y retorna (tools, client). Retorna ([], None) si NEON_API_KEY no está configurado."""
    if not NEON_API_KEY:
        logger.info("NEON_API_KEY no configurado — omitiendo integración Neon MCP")
        return [], None

    client = MultiServerMCPClient(
        {
            "neon": {
                "transport": "streamable_http",
                "url": "https://mcp.neon.tech/mcp",
                "headers": {
                    "Authorization": f"Bearer {NEON_API_KEY}"
                },
            }
        }
    )
    tools = await client.get_tools()
    return tools, client


DEMO_MCP_SERVER_NAME = "demo_mcp_server"


async def load_demo_mcp_tools() -> Tuple[list, MultiServerMCPClient | None]:
    """Conecta al demo MCP server (03_mcp_server, servicio HTTP propio — ver
    DEPLOYMENT.md) y retorna (tools, client). Retorna ([], None) si
    DEMO_MCP_SERVER_URL no está configurado.

    Se autentica con un ID token de Google (GoogleIDTokenAuth), necesario
    cuando 03_mcp_server corre como Cloud Run privado (--no-allow-unauthenticated);
    en dev local contra un server sin auth, el token simplemente no se agrega
    (fail-open, ver src/utils/gcp_auth.py).
    """
    if not DEMO_MCP_SERVER_URL:
        logger.info("DEMO_MCP_SERVER_URL no configurado — omitiendo integración con demo MCP server")
        return [], None

    client = MultiServerMCPClient(
        {
            DEMO_MCP_SERVER_NAME: {
                "transport": "streamable_http",
                "url": DEMO_MCP_SERVER_URL,
                # El endpoint incluye /mcp, pero Cloud Run exige como
                # audiencia el origen del servicio (sin path).
                "auth": GoogleIDTokenAuth(
                    audience=cloud_run_audience(DEMO_MCP_SERVER_URL)
                ),
            }
        }
    )
    tools = await client.get_tools()
    return tools, client


def diagnose_demo_mcp_server() -> str | None:
    """Arranca el demo MCP server una vez, a mano, para ver por qué se cae.

    El cliente MCP solo informa "Connection closed" cuando el subproceso muere. Aquí se
    ejecuta el mismo script con la entrada cerrada: un servidor sano termina sin error y
    uno roto deja su traceback, de donde se toma la última línea (por ejemplo, la
    variable de entorno que falta). Devuelve None si no encuentra nada raro."""
    if not DEMO_MCP_SERVER_PATH:
        return None
    import subprocess

    try:
        run = subprocess.run(
            [sys.executable, DEMO_MCP_SERVER_PATH],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"
    if run.returncode == 0:
        return None
    lines = [l for l in (run.stderr or "").strip().splitlines() if l.strip()]
    return lines[-1] if lines else f"el servidor terminó con código {run.returncode}"


async def load_demo_mcp_skills(client: MultiServerMCPClient | None) -> List[Dict[str, str]]:
    """Descubre las skills que expone el demo MCP server como recursos MCP
    (esquema skill://..., ver src/routes/skills.py en 03_mcp_server).

    Progressive disclosure: solo se listan name/description/uri de cada skill (barato,
    va al system prompt); el contenido completo se lee bajo demanda vía load_skill
    (ver agent_service.py), no acá. Retorna [] si no hay client o no expone skills."""
    if client is None:
        return []

    try:
        async with client.session(DEMO_MCP_SERVER_NAME) as session:
            result = await session.list_resources()
    except Exception as exc:
        logger.warning("Error listando skills del demo MCP server: %s", exc)
        return []

    skills: List[Dict[str, str]] = []
    for resource in result.resources:
        uri = str(resource.uri)
        if not uri.startswith("skill://"):
            continue
        skills.append(
            {
                "name": resource.name or uri,
                "description": resource.description or "",
                "uri": uri,
            }
        )
    return skills


def get_all_tools(mcp_tools: list | None = None) -> list:
    """Retorna las tools locales combinadas con las tools MCP opcionales."""
    all_tools = list(LOCAL_TOOLS)
    if mcp_tools:
        all_tools.extend(mcp_tools)
        logger.info("Cargadas %d tool(s) MCP: %s", len(mcp_tools), [t.name for t in mcp_tools])
    return all_tools
