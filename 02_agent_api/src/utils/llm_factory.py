"""Fábrica del modelo de chat. Cambia de OpenAI a Claude con LLM_PROVIDER, sin tocar código."""

from src.utils import environment as env


def build_chat_model(temperature: float | None = None):
    """Devuelve el chat model del proveedor configurado (LLM_PROVIDER)."""
    if env.LLM_PROVIDER == "anthropic":
        if not env.ANTHROPIC_API_KEY:
            raise RuntimeError("LLM_PROVIDER=anthropic requiere ANTHROPIC_API_KEY en el .env")
        from langchain_anthropic import ChatAnthropic

        kwargs = {"model": env.ANTHROPIC_MODEL, "api_key": env.ANTHROPIC_API_KEY}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return ChatAnthropic(**kwargs)

    if not env.OPENAI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=openai requiere OPENAI_API_KEY en el .env")
    from langchain_openai import ChatOpenAI

    kwargs = {"model": env.OPENAI_MODEL, "api_key": env.OPENAI_API_KEY}
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatOpenAI(**kwargs)
