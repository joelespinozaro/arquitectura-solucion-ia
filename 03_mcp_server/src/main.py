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

if __name__ == "__main__":
    logger.info("Iniciando InstitutoMCPServer (streamable-http, puerto %d)", MCP_SERVER_PORT)
    mcp.run(transport="streamable-http")
