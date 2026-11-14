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
| M5 · S1 Guardrails, red teaming y compliance | `m5-s1` | En preparación | Pendiente |
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

## Reglas

- Probado con Python 3.13, SQLAlchemy 2.1 y psycopg 3. Las cinco partes usan las mismas versiones de base de datos.
- Ningún secreto en el repositorio. Los `.env.example` tienen valores vacíos o de ejemplo.
- Las ramas `m4-s2*` conservan el historial del repositorio original `modulo4-sesion2-lab`.
