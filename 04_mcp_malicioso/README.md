# MCP malicioso (demo de clase)

Servidor de práctica para ver tool poisoning y rug pull. No hace nada dañino.

Se prueba con el script de la Agent API (desde `02_agent_api`, con el entorno virtual activo):

```bash
python -I scripts/mcp_review.py benigno --fijar      # aprueba la tool limpia y guarda su hash
python -I scripts/mcp_review.py envenenado           # descripción con instrucciones ocultas
python -I scripts/mcp_review.py rugpull --reiniciar  # borra el estado del rug pull
python -I scripts/mcp_review.py rugpull --fijar      # 1.ª conexión: limpia, se fija
python -I scripts/mcp_review.py rugpull              # 2.ª conexión: la descripción cambió
```

Los modos del servidor (`MALICIOSO_MODO`) son `benigno`, `envenenado` y `rugpull`.
El lock de la práctica vive en la carpeta temporal del sistema y no toca `config/mcp.lock.json`.
También hay tests en `tests/mcp_trust`.
