# loadtest: prueba de carga con Locust (M5S2, parte 4)

Mide la arquitectura propia (API, capas regex, base de datos) con un modelo simulado,
no los límites de velocidad de OpenAI o Groq.

```bash
# 1. Agente en modo simulado (desde 02_agent_api, con LLM_MODE=fake y LANGSMITH_TRACING=false en el .env)
uvicorn src.main:app --port 8080

# 2. Locust (desde loadtest)
pip install -r requirements.txt
locust -f locustfile.py --host http://localhost:8080          # interfaz en http://localhost:8089

# 3. Sin interfaz, y comparar contra el SLO de slo.yaml
locust -f locustfile.py --host http://localhost:8080 --headless -u 60 -r 10 -t 60s --csv resultados
python check_slo.py resultados_stats.csv
```

Si no se cumple el SLO, sube los workers y repite: `uvicorn src.main:app --port 8080 --workers 4`.
