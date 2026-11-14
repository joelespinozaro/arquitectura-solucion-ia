"""Servicio de escaneo de seguridad (API `/v1/scan/*`).

Expone como funciones puras las mismas reglas deterministas que usan las capas
del InputGuardrail (secretos, prompt injection, PII), para que otros sistemas
(el MCP, el gateway de WhatsApp, un pipeline externo) puedan pedir un veredicto
sin pasar por el agente.

Decisiones de diseño:
- Falla cerrado: si el escaneo lanza un error, el veredicto es `block`.
- Nunca devuelve ni registra el texto original. La auditoría guarda un hash
  corto, la decisión y las categorías encontradas.
- El PII se controla por petición (`pii_mode`): `block`, `mask` u `off`.
  Solo se consideran las entidades que la configuración
  (`pii_strategies.yaml`) no marca como `off` (así PERSON y LOCATION no
  generan falsos positivos).
- Secretos y canary tokens siempre bloquean, sin importar `pii_mode`.
"""
import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.services.guardrails.common import load_yaml_config
from src.services.guardrails.layer1_secrets import SECRET_PATTERNS
from src.services.guardrails.layer2_prompt_injection import _compile_patterns
from src.utils.logger import get_logger
from src.utils.pii import (
    PIIMatch,
    get_pii_score_threshold,
    get_pii_strategies,
    get_shared_pii_detector,
    mask_span,
)

logger = get_logger(__name__)

PII_MODES = ("block", "mask", "off")
MAX_TEXT_CHARS = 20_000

_INJECTION_PATTERNS: Optional[List[Tuple[str, re.Pattern]]] = None


def _injection_patterns() -> List[Tuple[str, re.Pattern]]:
    global _INJECTION_PATTERNS
    if _INJECTION_PATTERNS is None:
        _INJECTION_PATTERNS = _compile_patterns(load_yaml_config("prompt_injection_patterns.yaml"))
    return _INJECTION_PATTERNS


@dataclass
class Finding:
    layer: str
    category: str


@dataclass
class ScanResult:
    decision: str  # "allow" | "mask" | "block"
    text: Optional[str]  # texto saneado; None si se bloqueó
    findings: List[Finding] = field(default_factory=list)
    pii_mode: str = "mask"
    audit_id: str = ""


def _hash(text: str) -> str:
    # Prefijo con letra y "_": el filtro de PII de los logs no lo confunde con un DNI.
    return "h_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _pii_matches(text: str) -> List[PIIMatch]:
    detector, _ = get_shared_pii_detector()
    strategies = get_pii_strategies()
    matches = detector.analyze(text, get_pii_score_threshold())
    relevant = [m for m in matches if strategies.get(m.entity_type, "off") != "off"]
    # Descarta solapamientos: se queda con el primero de cada zona.
    relevant.sort(key=lambda m: (m.start, -(m.end - m.start)))
    kept: List[PIIMatch] = []
    for m in relevant:
        if kept and m.start < kept[-1].end:
            continue
        kept.append(m)
    return kept


def _mask_all(text: str, matches: List[PIIMatch]) -> str:
    for m in sorted(matches, key=lambda x: x.start, reverse=True):
        text = mask_span(text, m.start, m.end)
    return text


def _apply_pii(text: str, pii_mode: str, findings: List[Finding]) -> Tuple[str, bool]:
    """Devuelve (texto, bloquear). Agrega los hallazgos de PII."""
    if pii_mode == "off":
        return text, False
    matches = _pii_matches(text)
    if not matches:
        return text, False
    for m in matches:
        findings.append(Finding("pii", m.entity_type))
    if pii_mode == "block":
        return text, True
    return _mask_all(text, matches), False


def _finish(
    kind: str, text: str, pii_mode: str, findings: List[Finding], blocked: bool, sanitized: str
) -> ScanResult:
    if blocked:
        decision = "block"
    elif sanitized != text:
        decision = "mask"
    else:
        decision = "allow"
    audit_id = "aud_" + uuid.uuid4().hex[:12]
    logger.info(
        "scan_%s decision=%s pii_mode=%s text_hash=%s length=%d findings=%s audit_id=%s",
        kind,
        decision,
        pii_mode,
        _hash(text),
        len(text),
        sorted({f"{f.layer}:{f.category}" for f in findings}),
        audit_id,
        extra={"audit_id": audit_id, "text_hash": _hash(text)},
    )
    return ScanResult(
        decision=decision,
        text=None if blocked else sanitized,
        findings=findings,
        pii_mode=pii_mode,
        audit_id=audit_id,
    )


def _fail_closed(kind: str, text: str, pii_mode: str, exc: Exception) -> ScanResult:
    logger.warning("scan_%s error=%s", kind, type(exc).__name__)
    return _finish(kind, text, pii_mode, [Finding("scanner", "error")], True, text)


def _scan_secrets(text: str, findings: List[Finding]) -> bool:
    hit = any(p.search(text) for p in SECRET_PATTERNS)
    if hit:
        findings.append(Finding("secrets", "credential"))
    return hit


def scan_input(text: str, pii_mode: str = "mask") -> ScanResult:
    """Escanea un mensaje que va hacia el agente o hacia una tool."""
    findings: List[Finding] = []
    try:
        blocked = _scan_secrets(text, findings)
        for category, pattern in _injection_patterns():
            if pattern.search(text):
                findings.append(Finding("prompt_injection", category))
                blocked = True
                break
        sanitized, pii_block = _apply_pii(text, pii_mode, findings)
        return _finish("input", text, pii_mode, findings, blocked or pii_block, sanitized)
    except Exception as exc:  # noqa: BLE001 - falla cerrado
        return _fail_closed("input", text, pii_mode, exc)


def scan_output(
    text: str, pii_mode: str = "mask", canary_tokens: Optional[List[str]] = None
) -> ScanResult:
    """Escanea una respuesta del modelo (o de una tool) antes de entregarla."""
    findings: List[Finding] = []
    try:
        blocked = _scan_secrets(text, findings)
        lowered = text.lower()
        for token in canary_tokens or []:
            if token and token.lower() in lowered:
                findings.append(Finding("canary", "system_prompt_leak"))
                blocked = True
                break
        sanitized, pii_block = _apply_pii(text, pii_mode, findings)
        return _finish("output", text, pii_mode, findings, blocked or pii_block, sanitized)
    except Exception as exc:  # noqa: BLE001 - falla cerrado
        return _fail_closed("output", text, pii_mode, exc)
