import importlib

import pytest

from src.utils import environment as env


def _fabrica(monkeypatch, **attrs):
    for k, v in attrs.items():
        monkeypatch.setattr(env, k, v)
    from src.utils import llm_factory

    return importlib.reload(llm_factory)


def test_openai_por_defecto(monkeypatch):
    f = _fabrica(monkeypatch, LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-4o-mini")
    m = f.build_chat_model()
    assert m.__class__.__name__ == "ChatOpenAI"


def test_anthropic(monkeypatch):
    f = _fabrica(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-test", ANTHROPIC_MODEL="claude-haiku-5-5")
    m = f.build_chat_model(temperature=0)
    assert m.__class__.__name__ == "ChatAnthropic"


def test_anthropic_sin_llave(monkeypatch):
    f = _fabrica(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        f.build_chat_model()


def test_openai_sin_llave(monkeypatch):
    f = _fabrica(monkeypatch, LLM_PROVIDER="openai", OPENAI_API_KEY="")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        f.build_chat_model()
