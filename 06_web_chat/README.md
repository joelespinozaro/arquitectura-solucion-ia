# 06_web_chat: la web del asistente

Chat web sin build y sin dependencias (HTML, CSS y JS). Consume `02_agent_api` por SSE y muestra, como Claude o ChatGPT, qué hace el agente mientras responde.

## Qué incluye

- Conversaciones con sesiones e historial (barra lateral, agrupadas por fecha).
- Actividad en vivo por turno: guardrails, skill cargada, tool consultada y su resultado.
- Fuentes: chips numerados, panel con los fragmentos recuperados (con relevancia y metadatos) y tarjetas con imagen y fichas.
- Archivos generados por tools: descarga y vista previa de imágenes.
- Markdown seguro (se escapa todo antes de renderizar), copiar código, copiar respuesta, 👍/👎 (usa `POST /api/feedback`), reintentar y detener.
- Responsive (móvil con menú y panel como hoja inferior), tema claro y oscuro, `prefers-reduced-motion`.
- Modo demo sin servidor: `index.html?demo=1` (o en Ajustes). Útil como plan B en clase.

## Cómo correrla

Opción 1, servida por la propia API (recomendada):

```bash
cd 02_agent_api && uvicorn src.main:app --port 8080
# abre http://localhost:8080/chat/
```

Opción 2, estática aparte (la API debe estar en :8080 o configurarla en Ajustes):

```bash
cd 06_web_chat && python -m http.server 5500
# abre http://localhost:5500/
```

En Docker la imagen solo copia `02_agent_api`: monta la carpeta y define `WEB_CHAT_DIR=/ruta/06_web_chat`.

## Contrato con la API

| Endpoint | Uso |
|---|---|
| `POST /api/chat/stream` | SSE con los eventos de abajo |
| `GET /api/sessions/{user}` | ids de las conversaciones del usuario |
| `GET /api/history/{session_id}` | turnos guardados (con fuentes) |
| `POST /api/feedback` | 👍/👎 por `trace_id` |

Eventos SSE: `session`, `skill`, `tool_start`, `tool_end`, `done` (respuesta, fuentes, archivos, tokens) y `error`.

## Decisión de seguridad: la respuesta no se emite token a token

`OutputGuardrail` y `SafetyGuard` corren después del modelo. Si se enviaran los tokens crudos, un secreto o el canary saldría antes del filtro. Por eso se transmiten los **eventos** del agente en vivo y la **respuesta final** llega en `done`, ya revisada. La web la revela de forma progresiva solo como efecto visual.

## Límites conocidos

- El usuario es un alias en `localStorage`, no una cuenta (la versión con Firebase vive en `01_agent-app`).
- No hay subida de archivos del usuario: el agente actual no los procesa.
- La lista de conversaciones del navegador es local. Si cambias de equipo, se reconstruye desde `/api/sessions`.
