"""Genera config/mcp.lock.json con las tools aprobadas del demo MCP server.

Uso (con el servidor levantado, desde 02_agent_api):
    python -I scripts/mcp_pin.py

Revisa el resultado antes de hacer commit: el lock es lo que dice "estas
tools y no otras". Cualquier cambio posterior en descripción o esquema se
detecta como rug pull.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_mcp_adapters.client import MultiServerMCPClient  # noqa: E402

from src.services.mcp_trust import fingerprint, load_lock, review_description, write_lock  # noqa: E402
from src.services.tools import DEMO_MCP_SERVER_NAME  # noqa: E402
from src.utils.environment import DEMO_MCP_SERVER_URL  # noqa: E402


async def main() -> int:
    if not DEMO_MCP_SERVER_URL:
        print("Define DEMO_MCP_SERVER_URL")
        return 1
    client = MultiServerMCPClient({DEMO_MCP_SERVER_NAME: {"transport": "streamable_http", "url": DEMO_MCP_SERVER_URL}})
    tools = await client.get_tools()
    sospechosas = {t.name: review_description(t.description or "") for t in tools}
    if any(sospechosas.values()):
        print("No se fija: hay descripciones sospechosas:", {k: v for k, v in sospechosas.items() if v})
        return 2
    lock = load_lock()
    lock[DEMO_MCP_SERVER_NAME] = {t.name: fingerprint(t) for t in tools}
    write_lock(lock)
    print(f"Lock actualizado con {len(tools)} tool(s):", sorted(lock[DEMO_MCP_SERVER_NAME]))
    return 0


sys.exit(asyncio.run(main()))
