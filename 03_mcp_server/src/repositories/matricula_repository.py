"""Acceso a datos de matrícula y asesorías.

Los datos son ficticios y viven en archivos locales: data/estudiantes.json
(solo lectura) y data/asesorias.jsonl (se agrega una línea por solicitud).
En producción esto sería una base de datos con permisos de solo lectura
para estudiantes y escritura limitada para asesorías.
"""

import json
from pathlib import Path
from typing import Optional

from src.utils.environment import ASESORIAS_PATH, ESTUDIANTES_PATH

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _estudiantes_path() -> Path:
    return Path(ESTUDIANTES_PATH) if ESTUDIANTES_PATH else _DATA_DIR / "estudiantes.json"


def _asesorias_path() -> Path:
    return Path(ASESORIAS_PATH) if ASESORIAS_PATH else _DATA_DIR / "asesorias.jsonl"


def find_student_by_dni(dni: str) -> Optional[dict]:
    with _estudiantes_path().open(encoding="utf-8") as f:
        for student in json.load(f):
            if student["dni"] == dni:
                return student
    return None


def list_asesorias() -> list[dict]:
    path = _asesorias_path()
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_asesoria(record: dict) -> None:
    path = _asesorias_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
