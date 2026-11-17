"""Arma los mensajes que Promptfoo le manda al modelo: el MISMO prompt del agente + la pregunta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_agent_api"))

from prompts.render import render_system_prompt  # noqa: E402


def build(context):
    variables = context["vars"]
    return [
        {"role": "system", "content": render_system_prompt(variables["canary"])},
        {"role": "user", "content": variables["pregunta"]},
    ]
