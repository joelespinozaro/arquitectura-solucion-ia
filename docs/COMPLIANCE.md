# Cumplimiento: qué control del repo responde a qué marco

Mapa de trabajo para clase. No es asesoría legal: valida cada punto con el área legal de tu organización.

## Marcos que se revisan

| Marco | Qué pide, en simple |
|---|---|
| EU AI Act | Clasificar el sistema por riesgo, transparencia hacia la persona usuaria, supervisión humana, registro de eventos |
| ISO/IEC 42001 | Sistema de gestión de IA: políticas, riesgos, controles, mejora continua |
| SOC 2 | Controles demostrables de seguridad, disponibilidad y confidencialidad |
| GDPR | Minimización, base legal, derechos de las personas, seguridad |
| Perú: Ley 29733 y su reglamento | Protección de datos personales: finalidad, consentimiento, seguridad, derechos ARCO |
| Perú: Ley 31814 y su reglamento (DS 115-2025-PCM) | Uso responsable de la IA, con enfoque de riesgo y transparencia |

## Controles del repo

| Control | Dónde está | Marcos a los que ayuda |
|---|---|---|
| Minimización de datos en tools (solo lo necesario, DNI parcial) | `03_mcp_server/src/services/matricula_service.py` | GDPR, Ley 29733 |
| Validación estricta de entradas y límites de uso | `matricula_service.py` | SOC 2, ISO 42001 |
| Confirmación explícita antes de registrar una asesoría | `solicitar_asesoria` (servidor) | EU AI Act (supervisión humana), Ley 29733 (consentimiento) |
| Auditoría sin datos personales en claro (hash) | servicios de matrícula y `security_scan_service.py` | SOC 2, GDPR |
| Ofuscación de PII en logs | `src/utils/pii_log_filter.py` | GDPR, Ley 29733 |
| PII configurable por petición (block, mask, off) | `/v1/scan/*`, `OUTPUT_PII_MODE` | GDPR, Ley 29733 |
| Guardrails de entrada, de tools y de salida | `src/services/guardrails`, `middleware/tool_output_guardrail.py`, `middleware/output_guardrail.py` | ISO 42001, SOC 2 |
| Pinning y revisión de tools MCP, allowlist | `src/services/mcp_trust.py`, `config/mcp.lock.json` | SOC 2 (cadena de suministro), ISO 42001 |
| Red team repetible y en CI | `05_red_team`, `.github/workflows` | ISO 42001 (mejora continua), SOC 2 |
| Datos de práctica ficticios | `03_mcp_server/data/estudiantes.json` | GDPR, Ley 29733 |

## Brechas que hoy siguen abiertas (decláralas, no las escondas)

- Las evasiones del dataset marcadas `known_gap` (espaciado, leetspeak, invisibles, base64, relatos) no se bloquean con reglas.
- Falta transparencia explícita hacia la persona usuaria (aviso de que habla con una IA) en el frontend y en WhatsApp.
- No hay política de retención ni borrado del historial de chat ni de `asesorias.jsonl`.
- No hay registro de consentimiento para tratar el teléfono con fines comerciales.
- No hay inventario de modelos ni de proveedores (OpenAI, Groq, GCP) con su ubicación de datos.
- El límite de consultas está en memoria: no sirve con varias réplicas.

## Preguntas para decidir en clase

1. ¿Qué nivel de riesgo tendría este asistente si además decidiera matrículas o becas?
2. ¿Quién es responsable del tratamiento del teléfono y por cuánto tiempo se guarda?
3. ¿Qué evidencia mostrarías a un auditor y dónde vive?
