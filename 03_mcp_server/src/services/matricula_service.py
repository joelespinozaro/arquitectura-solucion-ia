"""Reglas de negocio de matrícula y asesoría, con controles de seguridad.

Controles que se aplican aquí (el servidor MCP es la última defensa antes de
tocar datos, no se confía en que el modelo mande siempre el formato correcto):

- Validación estricta de entradas (DNI, teléfono, programa, nombre).
- Mínimo dato de salida: nunca se devuelven correo, teléfono ni DNI completo.
- Límite de consultas por minuto, contra la enumeración de DNI.
- Auditoría sin datos personales crudos: el DNI se registra como hash corto.
- Confirmación explícita del lado del servidor para la acción con efecto.
"""

import hashlib
import re
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone

from src.repositories import matricula_repository as repo
from src.utils.environment import MATRICULA_RATE_LIMIT_PER_MINUTE
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROGRAMAS = [
    "Data Engineer",
    "Data Architect",
    "ML Engineer",
    "Data Visualization",
    "Marketing Analytics",
]
_DNI_RE = re.compile(r"^\d{8}$")
_PHONE_RE = re.compile(r"^9\d{8}$")
_DEDUP_WINDOW = timedelta(hours=24)


class ValidationError(ValueError):
    """La entrada no cumple el formato esperado."""


class RateLimitError(RuntimeError):
    """Demasiadas consultas en poco tiempo."""


class _SlidingWindow:
    def __init__(self, limit: int, seconds: float = 60.0) -> None:
        self.limit, self.seconds = limit, seconds
        self._hits: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self._hits and now - self._hits[0] > self.seconds:
            self._hits.popleft()
        if len(self._hits) >= self.limit:
            return False
        self._hits.append(now)
        return True


_limiter = _SlidingWindow(MATRICULA_RATE_LIMIT_PER_MINUTE)


def reset_rate_limiter(limit: int | None = None) -> None:
    """Reinicia el límite de consultas (usado por los tests)."""
    global _limiter
    _limiter = _SlidingWindow(limit if limit is not None else MATRICULA_RATE_LIMIT_PER_MINUTE)


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _short_name(full_name: str) -> str:
    parts = full_name.split()
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]


def _normalize_program(programa: str) -> str:
    wanted = " ".join(programa.split()).lower()
    for p in PROGRAMAS:
        if p.lower() == wanted:
            return p
    raise ValidationError("Programa no válido. Opciones: " + ", ".join(PROGRAMAS))


def consultar_estado(dni: str) -> dict:
    dni = (dni or "").strip()
    if not _DNI_RE.match(dni):
        raise ValidationError("El DNI debe tener exactamente 8 dígitos.")
    if not _limiter.allow():
        logger.warning("audit", extra={"tool": "estado_matricula", "resultado": "rate_limited"})
        raise RateLimitError("Demasiadas consultas seguidas. Intenta de nuevo en un minuto.")

    student = repo.find_student_by_dni(dni)
    logger.info(
        "audit",
        extra={"tool": "estado_matricula", "dni_hash": _hash_id(dni), "resultado": "ok" if student else "no_encontrado"},
    )
    if not student:
        return {"encontrado": False}
    return {
        "encontrado": True,
        "dni_parcial": "*****" + dni[-3:],
        "nombre": _short_name(student["nombre"]),
        "programa": student["programa"],
        "estado": student["estado"],
        "proxima_cuota": student["proxima_cuota"],
    }


def registrar_asesoria(programa: str, nombre: str, telefono: str, confirmado: bool) -> dict:
    programa = _normalize_program(programa)
    nombre = " ".join((nombre or "").split())
    if not 2 <= len(nombre) <= 80:
        raise ValidationError("El nombre debe tener entre 2 y 80 caracteres.")
    telefono = re.sub(r"[\s-]", "", telefono or "")
    if telefono.startswith("+51"):
        telefono = telefono[3:]
    if not _PHONE_RE.match(telefono):
        raise ValidationError("El teléfono debe ser un celular peruano de 9 dígitos que empieza con 9.")

    if not confirmado:
        return {"estado": "pendiente_confirmacion", "programa": programa, "nombre": nombre, "telefono_parcial": "******" + telefono[-3:]}

    now = datetime.now(timezone.utc)
    for rec in repo.list_asesorias():
        if rec["telefono_hash"] == _hash_id(telefono) and rec["programa"] == programa:
            if now - datetime.fromisoformat(rec["creado"]) < _DEDUP_WINDOW:
                return {"estado": "ya_registrada", "ticket": rec["ticket"], "programa": programa}

    ticket = "ASE-" + uuid.uuid4().hex[:8].upper()
    repo.append_asesoria(
        {"ticket": ticket, "creado": now.isoformat(), "programa": programa, "nombre": nombre, "telefono": telefono, "telefono_hash": _hash_id(telefono)}
    )
    logger.info("audit", extra={"tool": "solicitar_asesoria", "telefono_hash": _hash_id(telefono), "programa": programa, "resultado": "registrada"})
    return {"estado": "registrada", "ticket": ticket, "programa": programa}
