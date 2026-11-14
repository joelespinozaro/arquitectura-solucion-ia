import pytest

from src.utils.gcp_auth import cloud_run_audience


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://03-mcp-server-abc-uc.a.run.app/mcp",
            "https://03-mcp-server-abc-uc.a.run.app",
        ),
        ("http://localhost:8000/mcp", "http://localhost:8000"),
        (
            "https://service.example/mcp?debug=true#fragment",
            "https://service.example",
        ),
    ],
)
def test_cloud_run_audience_uses_service_origin(url: str, expected: str) -> None:
    assert cloud_run_audience(url) == expected


@pytest.mark.parametrize("url", ["", "/mcp", "localhost:8000/mcp"])
def test_cloud_run_audience_rejects_non_absolute_urls(url: str) -> None:
    with pytest.raises(ValueError, match="URL de servicio inválida"):
        cloud_run_audience(url)


def test_url_local_no_pide_token_de_google(monkeypatch):
    """En desarrollo local no se intenta obtener un ID token (evita esperas y avisos)."""
    from src.utils import gcp_auth

    llamadas = []
    monkeypatch.setattr(gcp_auth.GoogleIDTokenAuth, "_fetch_token", lambda self: llamadas.append(1) or "tok")
    auth = gcp_auth.GoogleIDTokenAuth(audience="http://localhost:8000")
    req = gcp_auth.httpx.Request("POST", "http://localhost:8000/mcp")
    next(auth.auth_flow(req))
    assert llamadas == []
    assert "Authorization" not in req.headers


def test_url_remota_si_pide_token(monkeypatch):
    from src.utils import gcp_auth

    monkeypatch.setattr(gcp_auth.GoogleIDTokenAuth, "_fetch_token", lambda self: "tok")
    auth = gcp_auth.GoogleIDTokenAuth(audience="https://mcp-abc.run.app")
    req = gcp_auth.httpx.Request("POST", "https://mcp-abc.run.app/mcp")
    next(auth.auth_flow(req))
    assert req.headers["Authorization"] == "Bearer tok"
