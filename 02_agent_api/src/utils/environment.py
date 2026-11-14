import os
import re
from pathlib import Path

from decouple import config

OPENAI_API_KEY: str = config("OPENAI_API_KEY")
OPENAI_MODEL: str = config("OPENAI_MODEL")

DATABASE_URL: str = config("DATABASE_URL")
HISTORY_LIMIT: int = config("HISTORY_LIMIT", default=10, cast=int)

NEON_API_KEY: str | None = config("NEON_API_KEY", default=None)
NEON_PROJECT_ID: str | None = config("NEON_PROJECT_ID", default=None)

# Raíz del repo: este archivo vive en <repo>/02_agent_api/src/utils/
REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_mcp_server_path(raw: str | None, repo_root: Path = REPO_ROOT, windows: bool = os.name == "nt") -> str | None:
    """Devuelve la ruta a 03_mcp_server/mcp_server.py sin que importe cómo se escribió.

    - Vacía: la busca sola en <repo>/03_mcp_server (no hace falta configurar nada).
    - "off": desactiva el servidor MCP.
    - Acepta / o \\ y la forma de Git Bash (/c/Projects/... se convierte en C:/Projects/...).
    - Si la ruta incluye por error la carpeta 02_agent_api (efecto de correr pwd ahí), la corrige.
    - Si es relativa, la resuelve desde la raíz del repo.
    Si nada existe devuelve la ruta tal cual, para que el error nombre lo que se escribió."""
    raw = (raw or "").strip().strip("\"'")
    if raw.lower() in {"off", "none", "false", "no"}:
        return None
    default = repo_root / "03_mcp_server" / "mcp_server.py"
    if not raw:
        return str(default) if default.is_file() else None
    if windows:
        m = re.match(r"^/([a-zA-Z])/(.*)$", raw)       # Git Bash: /c/Projects/x
        if m:
            raw = f"{m.group(1).upper()}:/{m.group(2)}"
    path = Path(raw)
    candidates = [path, repo_root / path]
    parts = list(path.parts)
    if "02_agent_api" in parts:                          # .../02_agent_api/03_mcp_server/...
        i = parts.index("02_agent_api")
        candidates.append(Path(*parts[:i], *parts[i + 1 :]))
    candidates.append(default)                           # último recurso: el del repo
    for c in candidates:
        if c.is_file():
            return str(c.resolve())
    return raw


DEMO_MCP_SERVER_PATH: str | None = resolve_mcp_server_path(config("DEMO_MCP_SERVER_PATH", default=None))

LANGSMITH_TRACING: bool = config("LANGSMITH_TRACING", default=False, cast=bool)
LANGSMITH_API_KEY: str | None = config("LANGSMITH_API_KEY", default=None)
LANGSMITH_PROJECT: str = config("LANGSMITH_PROJECT", default="agente-mcp")
LANGSMITH_ENDPOINT: str = config("LANGSMITH_ENDPOINT", default="https://api.smith.langchain.com")

# El SDK de LangSmith (usado internamente por langchain) lee estas variables
# directamente de las variables de entorno del proceso, no del config() de
# decouple, así que hay que propagarlas explícitamente a os.environ.
if LANGSMITH_TRACING and LANGSMITH_API_KEY:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_ENDPOINT", LANGSMITH_ENDPOINT)
    os.environ.setdefault("LANGSMITH_API_KEY", LANGSMITH_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", LANGSMITH_PROJECT)

# InputGuardrail (HU SEC-001) — Capas 7 y 8, servidas vía Groq API
GROQ_API_KEY: str = config("GROQ_API_KEY")
GROQ_PROMPT_GUARD_MODEL: str = config(
    "GROQ_PROMPT_GUARD_MODEL", default="meta-llama/Llama-Prompt-Guard-2-86M"
)
GROQ_LLAMA_GUARD_MODEL: str = config(
    "GROQ_LLAMA_GUARD_MODEL", default="openai/gpt-oss-safeguard-20b"
)
GROQ_TIMEOUT_SECONDS: float = config("GROQ_TIMEOUT_SECONDS", default=3, cast=float)

# InputGuardrail — Capa 4 (anti-ReDoS)
CUSTOM_REGEX_TIMEOUT_SECONDS: float = config("CUSTOM_REGEX_TIMEOUT_SECONDS", default=1, cast=float)

# Hooks (parte 3): presupuesto de tokens por conversación
TOKEN_BUDGET: int = config("TOKEN_BUDGET", default=8000, cast=int)
