import hmac
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from src.dto.api_entities import ScanFinding, ScanInputRequest, ScanOutputRequest, ScanResponse
from src.services import security_scan_service as svc
from src.utils.environment import SCAN_API_KEY

router = APIRouter(prefix="/v1/scan", tags=["scan"])


def _check_key(x_api_key: Optional[str]) -> None:
    """Si SCAN_API_KEY está definida, exige el header X-API-Key."""
    if not SCAN_API_KEY:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, SCAN_API_KEY):
        raise HTTPException(status_code=401, detail="API key inválida")


def _to_response(r: svc.ScanResult) -> ScanResponse:
    return ScanResponse(
        decision=r.decision,
        text=r.text,
        findings=[ScanFinding(layer=f.layer, category=f.category) for f in r.findings],
        pii_mode=r.pii_mode,
        audit_id=r.audit_id,
    )


@router.post("/input", response_model=ScanResponse)
def scan_input(req: ScanInputRequest, x_api_key: Optional[str] = Header(default=None)) -> ScanResponse:
    _check_key(x_api_key)
    return _to_response(svc.scan_input(req.text, req.pii_mode))


@router.post("/output", response_model=ScanResponse)
def scan_output(req: ScanOutputRequest, x_api_key: Optional[str] = Header(default=None)) -> ScanResponse:
    _check_key(x_api_key)
    return _to_response(svc.scan_output(req.text, req.pii_mode, req.canary_tokens))
