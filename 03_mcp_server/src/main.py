import socket
import sys

from mcp.server.fastmcp import FastMCP

from src.routes.knowledge import register_knowledge_tools
from src.routes.matricula import register_matricula_tools
from src.routes.skills import register_skill_resources
from src.utils.environment import MCP_SERVER_PORT
from src.utils.logger import get_logger

logger = get_logger(__name__)

mcp = FastMCP(
    "InstitutoMCPServer",
    log_level="ERROR",
    host="0.0.0.0",
    port=MCP_SERVER_PORT,
    dependencies=[
        "httpx",
        "python-decouple",
        "python-json-logger",
        "langchain-openai",
        "langchain-qdrant",
        "qdrant-client",
        "pyyaml",
    ],
)
register_knowledge_tools(mcp)
register_matricula_tools(mcp)
register_skill_resources(mcp)

def _puerto_ocupado(port: int) -> bool:
    """True si ya hay algo escuchando en el puerto.

    En Windows, uvicorn abre el socket con SO_REUSEADDR y puede arrancar
    "bien" aunque otro proceso (por ejemplo, el servidor MCP de una clase
    anterior) ya use el mismo puerto. Las peticiones siguen yendo al proceso
    viejo y el Inspector muestra tools que ya no existen. Por eso se revisa
    antes de arrancar.
    """
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    if _puerto_ocupado(MCP_SERVER_PORT):
        logger.error(
            "El puerto %d ya está en uso por otro proceso (quizá un servidor MCP anterior). "
            "Ciérralo y vuelve a intentar. Windows: netstat -ano | findstr :%d y luego "
            "taskkill /PID <número> /F. Mac/Linux: lsof -ti:%d | xargs kill",
            MCP_SERVER_PORT, MCP_SERVER_PORT, MCP_SERVER_PORT,
        )
        sys.exit(1)
    logger.info("Iniciando InstitutoMCPServer (streamable-http, puerto %d)", MCP_SERVER_PORT)
    mcp.run(transport="streamable-http")
