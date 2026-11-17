"""Modelo SIMULADO para ensayar el eval gate sin keys.

Lee el prompt del sistema y se comporta según lo que encuentre:
  - si el prompt todavía contiene la regla "Sé conciso", responde corto,
  - si alguien la borró o la cambió por otra, responde largo.
No es un modelo real: solo demuestra cómo un cambio de prompt se convierte en un check rojo.
"""
import json

CORTA = "Hola, soy el asistente del instituto. Puedo ayudarte con programas, cursos y matrículas."
LARGA = " ".join(
    ["Con gusto te explico todo en detalle, empezando por el contexto general de la pregunta."] * 12
)


def call_api(prompt, options, context):
    try:
        mensajes = json.loads(prompt)
        sistema = next(m["content"] for m in mensajes if m["role"] == "system")
    except (ValueError, StopIteration, TypeError):
        sistema = str(prompt)
    return {"output": CORTA if "conciso" in sistema.lower() else LARGA}
