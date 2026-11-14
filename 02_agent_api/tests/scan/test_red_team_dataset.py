"""Red team determinista: corre el dataset de 05_red_team contra el escáner."""
from pathlib import Path

import pytest
import yaml

from src.services import security_scan_service as svc
from src.utils.pii import RegexPIIDetector

DATASET = Path(__file__).resolve().parents[3] / "05_red_team" / "dataset.yaml"
DATA = yaml.safe_load(DATASET.read_text(encoding="utf-8"))
CASOS = DATA["casos"]


@pytest.fixture(autouse=True)
def detector_regex(monkeypatch):
    monkeypatch.setattr(svc, "get_shared_pii_detector", lambda: (RegexPIIDetector(), "regex"))


def veredicto(caso) -> str:
    return svc.scan_input(caso["texto"], pii_mode="off").decision


@pytest.mark.parametrize("caso", [c for c in CASOS if not c.get("known_gap")], ids=lambda c: c["id"])
def test_caso(caso):
    assert veredicto(caso) == caso["expected"], caso["texto"]


@pytest.mark.parametrize("caso", [c for c in CASOS if c.get("known_gap")], ids=lambda c: c["id"])
def test_huecos_conocidos_siguen_abiertos(caso):
    """Si un hueco se cierra, este test falla a propósito: quita known_gap del dataset."""
    assert veredicto(caso) != caso["expected"], f"{caso['id']} ya se bloquea: quita known_gap"


def test_umbrales_globales():
    ataques = [c for c in CASOS if c["expected"] == "block" and not c.get("known_gap")]
    controles = [c for c in CASOS if c["expected"] == "allow"]
    tasa = sum(veredicto(c) == "block" for c in ataques) / len(ataques)
    falsos = sum(veredicto(c) == "block" for c in controles)
    assert tasa >= DATA["umbrales"]["tasa_bloqueo_minima"]
    assert falsos <= DATA["umbrales"]["falsos_positivos_maximos"]
