# 07_evals: eval gate de prompts (M5S2, parte 3)

Mide si un cambio en `02_agent_api/prompts/system.md` empeora al asistente.

| Archivo | Para qué |
|---|---|
| `golden.yaml` | 10 casos con el comportamiento mínimo que el prompt debe garantizar |
| `promptfooconfig.yaml` | Eval real contra `gpt-4o-mini` (necesita `OPENAI_API_KEY`) |
| `promptfooconfig.ensayo.yaml` | Ensayo sin keys con un modelo simulado, para ver el gate cambiar de verde a rojo |
| `build_prompt.py` | Arma system prompt (el mismo del agente) + pregunta |

```bash
cd 07_evals
export OPENAI_API_KEY="sk-..."
npx promptfoo@0.125.1 eval              # eval real
npx promptfoo@0.125.1 view              # tabla de resultados en el navegador

# sin keys
npx promptfoo@0.125.1 eval -c promptfooconfig.ensayo.yaml --grader file://ensayo/juez_simulado.py
```

El workflow `.github/workflows/eval-gate.yml` corre el eval real en cada PR que toca el prompt y
falla si menos del 90% de los casos pasa. Se activa creando la variable de repositorio
`EVAL_GATE_ENABLED=true` y el secret `OPENAI_API_KEY`.
