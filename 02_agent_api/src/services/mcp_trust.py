"""Confianza en servidores MCP: allowlist, pinning de herramientas y revisión
de descripciones.

Amenazas que cubre (OWASP MCP Top 10):
- Tool poisoning: la descripción de una tool trae instrucciones ocultas.
- Rug pull: una tool aprobada cambia su descripción o su esquema después.
- Tools nuevas no aprobadas (scope creep).
- Servidores no autorizados.

Cómo funciona: `config/mcp.lock.json` guarda, por servidor, el hash
sha256 de cada tool aprobada (nombre + descripción + esquema). Al conectar,
cada tool se compara contra el lock y su descripción se revisa con patrones.

Modos (`MCP_TRUST_MODE`):
- enforce: descarta las tools que no pasan (recomendado en producción).
- warn   : las deja pasar pero registra una advertencia (útil para desarrollar).
- off    : sin verificación.
"""
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

LOCK_PATH = Path(__file__).resolve().parents[2] / "config" / "mcp.lock.json"

_SUSPICIOUS = [
    ("etiqueta_oculta", re.compile(r"<\s*(important|system|instructions?|secret)\s*>", re.I)),
    ("ignorar_instrucciones", re.compile(r"(ignora|olvida|ignore|disregard)\b.{0,40}\b(instruc|rules|reglas|prompt)", re.I | re.S)),
    ("ocultar_al_usuario", re.compile(r"(no le (digas|menciones)|do not (tell|mention)|don't (tell|mention)|sin que el usuario)", re.I)),
    ("exfiltracion", re.compile(r"(prompt del sistema|system prompt|\.ssh|api[_ ]?key|contraseña|password|dni del usuario)", re.I)),
    ("ruta_sensible", re.compile(r"(/etc/passwd|~/\.|\.env\b|id_rsa)", re.I)),
]


@dataclass
class Verdict:
    tool: str
    ok: bool
    reasons: List[str] = field(default_factory=list)


def _schema_of(tool: Any) -> Any:
    schema = getattr(tool, "args_schema", None)
    if isinstance(schema, dict):
        return schema
    if schema is not None and hasattr(schema, "model_json_schema"):
        return schema.model_json_schema()
    return {}


def fingerprint(tool: Any) -> str:
    """Hash estable de nombre + descripción + esquema de argumentos."""
    payload = json.dumps(
        {"name": tool.name, "description": tool.description or "", "schema": _schema_of(tool)},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def review_description(text: str) -> List[str]:
    """Devuelve categorías sospechosas encontradas en una descripción."""
    found: List[str] = []
    if any(unicodedata.category(c) == "Cf" for c in text):
        found.append("caracteres_invisibles")
    found.extend(name for name, rx in _SUSPICIOUS if rx.search(text))
    return found


def load_lock(path: Path = LOCK_PATH) -> Dict[str, Dict[str, str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("servers", {})
    except FileNotFoundError:
        return {}


def write_lock(servers: Dict[str, Dict[str, str]], path: Path = LOCK_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"servers": servers}, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_tools(
    server: str, tools: List[Any], lock: Optional[Dict[str, Dict[str, str]]] = None
) -> List[Verdict]:
    lock = load_lock() if lock is None else lock
    pinned = lock.get(server)
    verdicts: List[Verdict] = []
    for tool in tools:
        reasons = [f"descripcion:{c}" for c in review_description(tool.description or "")]
        if pinned is None:
            reasons.append("servidor_sin_lock")
        elif tool.name not in pinned:
            reasons.append("tool_no_aprobada")
        elif pinned[tool.name] != fingerprint(tool):
            reasons.append("cambio_de_hash")
        verdicts.append(Verdict(tool.name, not reasons, reasons))
    return verdicts


def filter_trusted_tools(
    server: str,
    tools: List[Any],
    mode: str,
    allowed_servers: Optional[List[str]] = None,
    lock: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Any]:
    """Aplica allowlist y pinning. Ver el modo en el docstring del módulo."""
    if mode == "off":
        return tools
    if allowed_servers is not None and server not in allowed_servers:
        logger.error("mcp_trust servidor_no_permitido server=%s mode=%s", server, mode)
        return [] if mode == "enforce" else tools
    accepted: List[Any] = []
    for tool, verdict in zip(tools, verify_tools(server, tools, lock)):
        if verdict.ok:
            accepted.append(tool)
            continue
        logger.error("mcp_trust tool_rechazada server=%s herramienta=%s razones=%s mode=%s", server, tool.name, verdict.reasons, mode)
        if mode != "enforce":
            accepted.append(tool)
    return accepted
