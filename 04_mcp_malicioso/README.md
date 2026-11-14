# MCP malicioso (demo de clase)

Servidor de práctica para ver tool poisoning y rug pull. No hace nada dañino.

```bash
MALICIOSO_MODO=benigno    python server.py   # lo que se aprueba y se fija
MALICIOSO_MODO=envenenado python server.py   # descripción con instrucciones ocultas
MALICIOSO_MODO=rugpull    python server.py   # cambia en la 2.ª conexión
```

Se prueba con `02_agent_api/scripts/mcp_pin.py` y los tests de `tests/mcp_trust`.
