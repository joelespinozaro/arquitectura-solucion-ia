import os
import sys
from pathlib import Path

# Variables mínimas para importar el servidor sin servicios externos.
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.repositories import matricula_repository as repo
from src.services import matricula_service as service


@pytest.fixture(autouse=True)
def aislar(tmp_path, monkeypatch):
    """Cada test escribe en su propio archivo y parte con el límite reiniciado."""
    monkeypatch.setattr(repo, "ASESORIAS_PATH", str(tmp_path / "asesorias.jsonl"))
    service.reset_rate_limiter(limit=5)
    yield
