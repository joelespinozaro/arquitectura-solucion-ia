# Arquitectura de Solución IA: laboratorios del curso

**AI Solution Architect · Datapath** · Joel Espinoza Rojas

Un solo repositorio con el código de todos los laboratorios. Cada sesión es una rama. Las guías paso a paso viven en un sitio aparte:

**https://joelespinozaro.github.io/ai-solution-architect/**

## Cómo trabajar

```bash
git clone https://github.com/joelespinozaro/arquitectura-solucion-ia.git
cd arquitectura-solucion-ia
git branch -r                      # ver todas las ramas
git switch m4-s2-p2-skills         # cambiar a la parte del laboratorio que toca
```

Este `main` no tiene código de laboratorio, solo este índice.

## Sesiones

| Sesión | Rama | Guía | Estado |
|---|---|---|---|
| M4 · S2 Skills, hooks y production-grade | `m4-s2` (estado final) | [Guía](https://joelespinozaro.github.io/ai-solution-architect/m4-s2/) · [Laboratorio](https://joelespinozaro.github.io/ai-solution-architect/m4-s2/laboratorio/) | Disponible |
| M5 · S1 Guardrails, red teaming y compliance | `m5-s1` (estado final) | [Guía](https://joelespinozaro.github.io/ai-solution-architect/m5-s1/) · [Laboratorio](https://joelespinozaro.github.io/ai-solution-architect/m5-s1/laboratorio/) | Disponible |
| M5 · S2 LLMOps y observabilidad | `m5-s2` | En preparación | Pendiente |
| M4 · S1 Agent architecture y multiagente | `m4-s1` | Próximamente | Por migrar desde `modulo4-sesion1-lab` |
| M2 · S2 Data pipelines | `m2-s2` | Próximamente | Por migrar desde `lab_pipelines` |

## M4 · S2: una rama por parte del laboratorio

| Rama | Qué agrega | Qué observar |
|---|---|---|
| `m4-s2-p1-base` | Parte 1: agente con RAG conectado a WhatsApp (WAHA y gateway) | Un mensaje de ida y vuelta desde tu celular |
| `m4-s2-p2-skills` | `SkillMiddleware` y la tool `load_skill` | `load_skill` aparece solo cuando la pregunta lo necesita |
| `m4-s2-p3-hooks` | Logging, `TokenBudget`, `SafetyGuard` y `Retry` | El orden de ida y vuelta en la consola y el corte por presupuesto |
| `m4-s2-p4-guardrails` | 8 capas de guardrails, skills servidas por MCP y `pytest` | Qué capa bloquea cada ataque |
| `m4-s2-p5-produccion` | Opcional: Model Armor, evaluación con RAGAS y despliegue en GCP | `DEPLOYMENT.md` |
| `m4-s2` | Igual a `m4-s2-p5-produccion`: estado final de la sesión | |

Cada rama contiene el laboratorio completo hasta esa parte. No hace falta combinar ramas: se cambia de una a otra con `git switch`.

## M5 · S1: una rama por parte del laboratorio

| Rama | Qué agrega | Qué observar |
|---|---|---|
| `m5-s1-p1-mcp-estable` | MCP del instituto: tools `estado_matricula` y `solicitar_asesoria`, skills por programa | Las 3 tools y 6 skills en el MCP Inspector |
| `m5-s1-p2-mcp-seguridad` | Pinning y allowlist de tools MCP, revisión de descripciones, servidor malicioso (`04_mcp_malicioso`) | Un servidor envenenado y un rug pull rechazados |
| `m5-s1-p3-output-guardrails` | Servicio `/v1/scan/*` con PII configurable, guardrails de tools y de salida, canary | La misma entrada con `mask`, `block` y `off` |
| `m5-s1-p4-red-team` | Dataset de red team (`05_red_team`), Promptfoo, GitHub Actions, `docs/COMPLIANCE.md` | Tasa de bloqueo y huecos conocidos |
| `m5-s1` | Igual a `m5-s1-p4-red-team`: estado final de la sesión | |

Cada rama incluye a la anterior. En `m5-s1-p3` y `m5-s1-p4` el agente necesita `.env` (copia `.env.example`).

## Reglas

- Probado con Python 3.13, SQLAlchemy 2.1 y psycopg 3. Las cinco partes usan las mismas versiones de base de datos.
- Ningún secreto en el repositorio. Los `.env.example` tienen valores vacíos o de ejemplo.
- Las ramas `m5-s1*` parten de `m4-s2`, así que conservan también ese historial.
- Las ramas `m4-s2*` conservan el historial del repositorio original `modulo4-sesion2-lab`.
