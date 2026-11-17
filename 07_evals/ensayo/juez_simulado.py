"""Juez SIMULADO (reemplaza al modelo que corrige los llm-rubric) para el ensayo sin keys."""
import json


def call_api(prompt, options, context):
    return {"output": json.dumps({"pass": True, "score": 1, "reason": "juez simulado"})}
