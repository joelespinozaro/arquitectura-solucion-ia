"""resolve_mcp_server_path: la ruta del servidor MCP funciona sin importar cómo se escriba."""
from pathlib import Path

from src.utils.environment import resolve_mcp_server_path


def _repo(tmp_path):
    f = tmp_path / "03_mcp_server" / "mcp_server.py"
    f.parent.mkdir()
    f.write_text("")
    return tmp_path, str(f.resolve())


def test_vacia_la_busca_sola(tmp_path):
    repo, esperado = _repo(tmp_path)
    assert resolve_mcp_server_path("", repo, windows=False) == esperado
    assert resolve_mcp_server_path(None, repo, windows=False) == esperado


def test_off_la_desactiva(tmp_path):
    repo, _ = _repo(tmp_path)
    assert resolve_mcp_server_path("off", repo, windows=False) is None


def test_sin_carpeta_y_vacia_no_hay_servidor(tmp_path):
    assert resolve_mcp_server_path("", tmp_path, windows=False) is None


def test_ruta_absoluta_valida(tmp_path):
    repo, esperado = _repo(tmp_path)
    assert resolve_mcp_server_path(esperado, repo, windows=False) == esperado


def test_ruta_con_02_agent_api_de_mas(tmp_path):
    repo, esperado = _repo(tmp_path)
    mala = str(repo / "02_agent_api" / "03_mcp_server" / "mcp_server.py")
    assert resolve_mcp_server_path(mala, repo, windows=False) == esperado


def test_ruta_relativa_desde_la_raiz(tmp_path):
    repo, esperado = _repo(tmp_path)
    assert resolve_mcp_server_path("03_mcp_server/mcp_server.py", repo, windows=False) == esperado


def test_forma_git_bash_en_windows(tmp_path):
    repo, esperado = _repo(tmp_path)
    # /c/x en Windows se vuelve C:/x; aquí no existe, así que cae al servidor del repo
    assert resolve_mcp_server_path("/c/Projects/otra/03_mcp_server/mcp_server.py", repo, windows=True) == esperado


def test_ruta_inexistente_se_devuelve_tal_cual_si_no_hay_default(tmp_path):
    assert resolve_mcp_server_path("/no/existe/mcp_server.py", tmp_path, windows=False) == "/no/existe/mcp_server.py"
