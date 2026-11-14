"""Practica de confianza MCP: conecta al servidor malicioso y muestra el veredicto.

Uso (desde 02_agent_api, con el entorno virtual activo):
    python -I scripts/mcp_review.py benigno --fijar     # aprueba la tool limpia
    python -I scripts/mcp_review.py envenenado          # tool poisoning
    python -I scripts/mcp_review.py rugpull --reiniciar # borra estado y lock del rug pull
    python -I scripts/mcp_review.py rugpull --fijar     # 1.ª conexión: limpia, se fija
    python -I scripts/mcp_review.py rugpull             # 2.ª conexión: la descripción cambió

El lock de esta práctica vive en la carpeta temporal del sistema, no toca
config/mcp.lock.json. El servidor malicioso no hace nada dañino.
"""
import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_mcp_adapters.client import MultiServerMCPClient  # noqa: E402

from src.services.mcp_trust import fingerprint, load_lock, review_description, verify_tools, write_lock  # noqa: E402

SERVIDOR = Path(__file__).resolve().parents[2] / "04_mcp_malicioso" / "server.py"
TMP = Path(tempfile.gettempdir())
ESTADO = TMP / "mcp_malicioso_conexiones"
LOCK = TMP / "mcp_malicioso.lock.json"
NOMBRE = "malo"


async def traer_tools(modo: str):
    env = {**os.environ, "MALICIOSO_MODO": modo, "MALICIOSO_ESTADO": str(ESTADO)}
    client = MultiServerMCPClient(
        {NOMBRE: {"transport": "stdio", "command": sys.executable, "args": [str(SERVIDOR)], "env": env}}
    )
    return await client.get_tools()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["benigno", "envenenado", "rugpull"])
    ap.add_argument("--fijar", action="store_true", help="aprueba las tools actuales y guarda su hash")
    ap.add_argument("--reiniciar", action="store_true", help="borra el contador de conexiones y el lock de la práctica")
    args = ap.parse_args()

    if args.reiniciar:
        for f in (ESTADO, LOCK):
            f.unlink(missing_ok=True)
        print("Estado y lock de la práctica borrados.")
        return 0

    tools = await traer_tools(args.modo)
    for t in tools:
        print(f"\nTool: {t.name}")
        print(f"Descripción: {t.description}")
        hallazgos = review_description(t.description or "")
        print("Revisión de la descripción:", hallazgos or "sin hallazgos")

        if args.fijar and hallazgos:
            print("No se fija: la descripción es sospechosa.")
            return 2

    if args.fijar:
        lock = load_lock(LOCK)
        lock[NOMBRE] = {t.name: fingerprint(t) for t in tools}
        write_lock(lock, LOCK)
        print(f"\nLock guardado con {len(tools)} tool(s): {sorted(lock[NOMBRE])}")
        return 0

    lock = load_lock(LOCK)
    print("\nVeredicto contra el lock:")
    rechazada = False
    for v in verify_tools(NOMBRE, tools, lock):
        estado = "ACEPTADA" if v.ok else "RECHAZADA"
        rechazada = rechazada or not v.ok
        print(f"  {v.tool}: {estado} {v.reasons if v.reasons else ''}")
    return 1 if rechazada else 0


sys.exit(asyncio.run(main()))
