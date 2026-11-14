# Módulo 4 · Sesión 2 · Laboratorio de Skills, Hooks y patrones production-grade

**AI Solution Architect · Datapath** · Joel Espinoza Rojas

En la Sesión 1 el asistente del instituto aprendió a razonar, usar tools y responder con RAG. Funcionaba en el notebook. En este laboratorio lo conectamos a WhatsApp, con alumnos reales, y le agregamos lo que hace falta para que no se rompa:

| Problema en producción | Pieza que lo resuelve | Parte |
|---|---|---|
| El system prompt crece y cada mensaje arrastra todas las reglas | **Skills** que se cargan solo cuando la pregunta las necesita | 2 |
| Nadie sabe qué pasó ni cuánto costó una conversación | **Hooks** de logging y presupuesto de tokens | 3 |
| El proveedor del modelo falla en hora punta | **Retry** con espera creciente | 3 |
| Un alumno intenta manipular al agente o pega datos personales | **Guardrails** en 8 capas, fail-close | 4 |
| Un cambio rompe algo y nadie se entera | **Test suite** con pytest | 4 |

## Guías

Las guías interactivas viven publicadas (una sola versión):

- Conceptos de la sesión: https://joelespinozaro.github.io/ai-solution-architect/m4-s2/
- Paso a paso del laboratorio: https://joelespinozaro.github.io/ai-solution-architect/m4-s2/laboratorio/

## Carpetas

- **waha** levanta WhatsApp como API con `docker compose`.
- **01_data_setup** crea las tablas de PostgreSQL y carga los documentos del instituto en Qdrant. Si ya lo hiciste en la sesión de RAG, puedes saltarlo.

## Una rama por parte

Cada rama suma una capa a la anterior. Para ver qué cambió entre dos partes: `git diff m4-s2-p2-skills m4-s2-p3-hooks -- 02_agent_api`.

| Rama | Qué agrega | Qué observar |
|---|---|---|
| `m4-s2-p1-base` | Parte 1: agente con RAG + WhatsApp (WAHA + gateway) | Un mensaje de ida y vuelta desde tu celular |
| `m4-s2-p2-skills` | `SkillMiddleware` y la tool `load_skill` | En el log, `load_skill` aparece solo cuando la pregunta lo necesita |
| `m4-s2-p3-hooks` | Middlewares de logging, `TokenBudget`, `SafetyGuard` y `Retry` | El orden de ida y vuelta en la consola, y el corte por presupuesto |
| `m4-s2-p4-guardrails` | 8 capas de guardrails, skills servidas por MCP, `pytest` | Qué capa bloquea cada ataque y `pytest tests/guardrails -q` |
| `m4-s2-p5-produccion` | Opcional: Model Armor, evaluación con RAGAS y despliegue en GCP | Ver `DEPLOYMENT.md` |

## Cómo empezar

Requisitos: Python 3.11+, Docker, una API key de OpenAI, PostgreSQL y Qdrant con datos (ver `01_data_setup`). Desde la parte 4 también una API key gratuita de [Groq](https://console.groq.com/keys).

```bash
git clone <url-de-este-repo>
cd <carpeta-del-repo>

# 1. WAHA (sin rutas dentro de comandos: sirve en Git Bash, PowerShell, macOS y Linux)
cd waha
cp .env.example .env        # cambia WAHA_API_KEY y WAHA_DASHBOARD_PASSWORD
docker compose up -d
cd ..

# 2. Agent API (terminal 1)
cd 02_agent_api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # completa OPENAI_API_KEY, DATABASE_URL y QDRANT_*
python -m src.main          # :8080

# 3. Gateway (terminal 2)
cd 02_chatbot_gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# crea .env con CHATBOT_API_URL, WAHA_API_URL y WAHA_API_KEY (ver el .env.example)
python -m src.main          # :8090
```

Luego, en `http://localhost:3030/dashboard` (usuario y clave de `waha/.env`): la sesión `default` ya arranca sola y el webhook ya está registrado. Solo escanea el QR con un número de pruebas.

Para pasar a la siguiente parte: `git switch m4-s2-p2-skills` y reinicia el Agent API.

## Guía paso a paso

La guía interactiva del laboratorio (capturas, variables y solución de errores) está publicada en
https://joelespinozaro.github.io/ai-solution-architect/m4-s2/laboratorio/ y la de conceptos en
https://joelespinozaro.github.io/ai-solution-architect/m4-s2/. Ya no vive dentro de este repositorio: así hay una sola versión.

### Si WAHA falla con "target directory does not exist"

Pasaba con `docker run -v "$(pwd)":/app/env ... init-waha /app/env` en Git Bash de Windows, que convierte `/app/env` en una ruta de Windows. Con `docker compose` ya no ocurre. Si usas el comando antiguo, anteponle `MSYS_NO_PATHCONV=1`.

## Seguridad

- Nunca subas un `.env`. Este repo los ignora en `.gitignore`.
- Usa un número de WhatsApp de pruebas, no tu número personal.
- Sin `GROQ_API_KEY`, las capas 7 y 8 bloquean todos los mensajes a propósito (fail-close).
