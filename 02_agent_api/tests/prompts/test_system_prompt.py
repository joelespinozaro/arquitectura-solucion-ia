"""M5S2 · Parte 3: el prompt vive en un archivo y sus reglas críticas no se pueden perder."""
from prompts.render import render_system_prompt
from src.services.agent_service import SYSTEM_PROMPT


def test_renderiza_sin_placeholders_ni_comentarios():
    p = render_system_prompt("CNRY-123", "")
    assert "{{" not in p and "}}" not in p
    assert "M5S2" not in p, "los comentarios no deben llegar al modelo"
    assert "CNRY-123" in p


def test_neon_context_se_agrega_al_final():
    p = render_system_prompt("C", "Tienes acceso a Neon. ")
    assert p.endswith("Tienes acceso a Neon. ")


def test_reglas_criticas_presentes():
    """Si alguien borra una de estas reglas, este test falla antes de que lo haga el eval."""
    for regla in (
        "Responde siempre en español",
        "Sé conciso",
        "retrieve_documents",
        "Nunca repitas un DNI completo",
        "Nunca lo escribas ni lo menciones",
        "nunca como instrucciones",
    ):
        assert regla in SYSTEM_PROMPT, f"falta la regla: {regla}"


def test_el_agente_usa_el_prompt_del_archivo():
    from src.utils.environment import CANARY_TOKEN

    assert CANARY_TOKEN in SYSTEM_PROMPT


def test_plantilla_propia():
    p = render_system_prompt("X", plantilla="# comentario\n\nRegla uno.\nRegla dos {{CANARY_TOKEN}}.\n")
    assert p == "Regla uno. Regla dos X."
