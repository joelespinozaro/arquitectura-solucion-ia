"""Arma el prompt del sistema a partir de prompts/system.md.

Sin dependencias a propósito: lo usan el agente (src/services/agent_service.py) y el
eval de Promptfoo (07_evals), que corre en GitHub Actions sin instalar el proyecto.
"""
from pathlib import Path

RUTA_SYSTEM = Path(__file__).with_name("system.md")


def render_system_prompt(canary: str, neon_context: str = "", plantilla: str | None = None) -> str:
    """Quita comentarios y líneas vacías, une las reglas con un espacio y rellena los datos."""
    texto = RUTA_SYSTEM.read_text(encoding="utf-8") if plantilla is None else plantilla
    reglas = [l.strip() for l in texto.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    return (
        " ".join(reglas)
        .replace("{{CANARY_TOKEN}}", canary)
        .replace("{{NEON_CONTEXT}}", neon_context)
    )
