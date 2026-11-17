# Despliegue en Google Cloud: clase M5S2 (17/11/2026)

> Paso a paso para alumnos: guía del laboratorio M5S2, **Parte 5** (joelespinozaro.github.io/ai-solution-architect/m5-s2/laboratorio/#r7). Este archivo es el registro del despliegue de la demo en clase.

Demo en vivo del profesor: el agente del instituto (`02_agent_api` + `06_web_chat`) y el servidor MCP (`03_mcp_server`) corriendo en Cloud Run, con imágenes construidas en Cloud Build y secretos en Secret Manager. Desplegado desde la rama `m5-s2` (commit `239a10a`).

## Datos del despliegue

| Dato | Valor |
|---|---|
| Proyecto | `arquitectura-solucion-ia` (proyecto del profesor) |
| Región | `us-central1` |
| Facturación | cuenta de facturación del profesor, vinculada al proyecto |
| Artifact Registry | `us-central1-docker.pkg.dev/arquitectura-solucion-ia/instituto` |
| Service account de runtime | `agente-runtime@arquitectura-solucion-ia.iam.gserviceaccount.com` |
| agent-api (público) | `https://agent-api-<hash>.a.run.app` (se borra después de clase) |
| Chat web | `<URL de agent-api>/chat/` |
| mcp-server (privado, solo `run.invoker` de la SA) | `https://mcp-server-<hash>.a.run.app` |
| LangSmith | proyecto `instituto-cloudrun` |
| Qdrant | colección `data-academy` (217 fragmentos) |

```
Navegador / Postman ──HTTPS──▶ Cloud Run agent-api (4 CPU, 4 Gi, min 1, max 3)
                                  │  guardrails locales + Groq, historial en Neon, trazas a LangSmith
                                  │  HTTPS + ID token de Google (SA con roles/run.invoker)
                                  ▼
                               Cloud Run mcp-server (2 CPU, 2 Gi, max 3, privado) ── Qdrant Cloud + embeddings OpenAI
```

## Secretos (Secret Manager, sin valores aquí)

| Secreto | Variable | Servicio |
|---|---|---|
| `openai-api-key` | `OPENAI_API_KEY` | ambos |
| `qdrant-api-key` | `QDRANT_API_KEY` | mcp-server |
| `database-url` | `DATABASE_URL` | agent-api |
| `groq-api-key` | `GROQ_API_KEY` | agent-api |
| `langsmith-api-key` | `LANGSMITH_API_KEY` | agent-api |
| `scan-api-key` | `SCAN_API_KEY` | agent-api (generado nuevo, `openssl rand -hex 16`) |

Cada secreto tiene `roles/secretmanager.secretAccessor` solo para la SA de runtime. Para leer la scan key: `gcloud secrets versions access latest --secret=scan-api-key`.

## Archivos de esta rama

- `Dockerfile.agent-cloudrun`: imagen del agente con contexto en la raíz, incluye `06_web_chat` en `/web_chat` (`WEB_CHAT_DIR`).
- `cloudbuild.agent.yaml`: build con ese Dockerfile.
- `.gcloudignore` (raíz): lista blanca, solo sube `02_agent_api`, `06_web_chat` y el Dockerfile (137 archivos, ningún `.env`).
- `03_mcp_server/.gcloudignore`: excluye `.env`, venvs y `data/asesorias.jsonl`.

## Comandos ejecutados (Git Bash)

```bash
export PROJECT_ID="arquitectura-solucion-ia" REGION="us-central1" AR_REPOSITORY="instituto"
export SA_NAME="agente-runtime"; export SERVICE_SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export MCP_SERVICE="mcp-server" AGENT_SERVICE="agent-api"

gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud billing projects link "$PROJECT_ID" --billing-account=<ID_CUENTA_FACTURACION>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com
gcloud artifacts repositories create "$AR_REPOSITORY" --repository-format=docker --location="$REGION"
gcloud iam service-accounts create "$SA_NAME" --display-name="Runtime del agente del instituto"
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_SA" \
  --member="user:$(gcloud config get-value account)" --role="roles/iam.serviceAccountUser"

# Secretos: valor leído del .env (sin \r ni comillas) y pasado por stdin
#   printf %s "$VALOR" | gcloud secrets versions add <id> --data-file=-
#   gcloud secrets add-iam-policy-binding <id> --member="serviceAccount:$SERVICE_SA" --role=roles/secretmanager.secretAccessor

# MCP
gcloud builds submit 03_mcp_server --tag="$MCP_IMAGE"
gcloud run deploy "$MCP_SERVICE" --image="$MCP_IMAGE" --region="$REGION" \
  --no-allow-unauthenticated --service-account="$SERVICE_SA" \
  --port=8080 --cpu=2 --memory=2Gi --max-instances=3 --session-affinity \
  --env-vars-file="$(cygpath -m mcp-env.yaml)" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,QDRANT_API_KEY=qdrant-api-key:latest"
gcloud run services add-iam-policy-binding "$MCP_SERVICE" --region="$REGION" \
  --member="serviceAccount:${SERVICE_SA}" --role="roles/run.invoker"

# Agente
gcloud builds submit . --config=cloudbuild.agent.yaml --substitutions=_IMAGE="$AGENT_IMAGE"
gcloud run deploy "$AGENT_SERVICE" --image="$AGENT_IMAGE" --region="$REGION" \
  --allow-unauthenticated --service-account="$SERVICE_SA" \
  --port=8080 --cpu=4 --memory=4Gi --timeout=300 --min-instances=1 --max-instances=3 \
  --env-vars-file="$(cygpath -m agent-env.yaml)" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest,GROQ_API_KEY=groq-api-key:latest,LANGSMITH_API_KEY=langsmith-api-key:latest,SCAN_API_KEY=scan-api-key:latest"
```

`agent-env.yaml` (no sensible): `OPENAI_MODEL=gpt-4o-mini`, `HISTORY_LIMIT=10`, `DEMO_MCP_SERVER_URL=<mcp>/mcp` (sin barra final), `GUARDRAIL_ENGINE=local`, modelos Groq de Prompt Guard y Llama Guard, `GROQ_TIMEOUT_SECONDS=3`, `TOKEN_BUDGET=8000`, `LANGSMITH_TRACING=true`, `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`, `LANGSMITH_PROJECT=instituto-cloudrun`, `MCP_TRUST_MODE=warn`, `CANARY_TOKEN=CNRY-gcp-clase`, `LLM_MODE=real`.

Tiempos de build: MCP 1 min 44 s, agente 6 min 30 s.

## Verificación (17/11/2026)

| Prueba | Resultado |
|---|---|
| `GET /docs` y `GET /chat/` | 200 y 200 |
| MCP sin token / con ID token | 403 / 200 (`initialize`) |
| Pregunta de programas (Data Engineering) | Respuesta con datos reales, `sources` con `retrieve_documents` y 4 contextos |
| Inyección "Ignora todas tus instrucciones..." | Bloqueada por guardrails (menos de 1 s) |
| `/v1/scan/input` con DNI y `X-API-Key` | `decision: mask`, `DNI_PE` |
| `/v1/scan/input` sin key | 401 |
| Chat web | Eventos visibles (guardrails, Qdrant), respuesta, fuente e historial |
| LangSmith `instituto-cloudrun` | Trazas `chat` en estado success |
| `pytest -q` en `02_agent_api` | 197 passed (con `SCAN_API_KEY` vacía, ver problemas) |

## Problemas y solución

1. **Facturación cerrada en el proyecto inicial.** El primer proyecto no tenía facturación activa. Se usó otro proyecto y se le vinculó una cuenta de facturación abierta.
2. **`500` en `/api/chat`: `column "latency_ms" of relation "history" does not exist`.** La base Neon no tenía las migraciones de M5S2. Se aplicaron `02_agent_api/setup/feedback_migration.sql` y `setup/observabilidad_migration.sql` (aditivas, `IF NOT EXISTS`). **Si se usa otra base, aplicarlas antes de desplegar.**
3. **20 tests de `tests/scan` fallaban en local.** El `.env` local define `SCAN_API_KEY`, entonces `/v1/scan` exige el header y los tests reciben 401. Con `SCAN_API_KEY=` vacía pasan 197. No es un fallo del código.
4. **`.gcloudignore` raíz.** Sin lista blanca se subían más de 600 archivos (`01_agent-app/.next`). Ahora sube solo lo necesario.
5. **Rutas en Git Bash.** `gcloud` es un ejecutable de Windows: los YAML se pasan con `cygpath -m`, no con `/tmp/...`.
6. **`LANGSMITH_ENDPOINT` vacío.** Si va como `""` en el YAML, el código no usa su default y las trazas fallan. Se fija explícito.
7. **curl de Git Bash con tildes.** El JSON inline con tildes llega mal codificado (`error parsing the body`). Para probar desde Git Bash, mandar el cuerpo desde un archivo UTF-8 con `--data-binary @archivo.json`. Postman y el chat web no tienen este problema.
8. **Calidad del RAG.** La pregunta genérica "¿Qué programas ofrece el instituto?" recupera fragmentos de sedes y reglamento y responde poco. Preguntas concretas ("¿Qué aprendo en Data Engineering y cuánto dura?", "modalidades de pago") responden bien. Es comportamiento de la búsqueda, igual que en local.

## Después de clase

```bash
# Dejar de pagar la instancia caliente
gcloud run services update agent-api --region=us-central1 --min-instances=0

# Borrar todo (solo cuando se decida)
gcloud run services delete agent-api --region=us-central1 --quiet
gcloud run services delete mcp-server --region=us-central1 --quiet
for s in openai-api-key qdrant-api-key database-url groq-api-key langsmith-api-key scan-api-key; do gcloud secrets delete "$s" --quiet; done
gcloud artifacts repositories delete instituto --location=us-central1 --quiet
# Opcional: desvincular facturación
gcloud billing projects unlink arquitectura-solucion-ia
```
