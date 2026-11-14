import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.chat import chat_router
from src.utils.logger import get_logger

logger = get_logger(__name__)


app = FastAPI(
    title="Agente Simple",
    description="Asistente simple",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

# Web chat (06_web_chat): si la carpeta existe (repo completo o WEB_CHAT_DIR), se sirve en /chat/
_web_dir = Path(os.getenv("WEB_CHAT_DIR") or Path(__file__).resolve().parents[2] / "06_web_chat")
if (_web_dir / "index.html").is_file():
    from fastapi.staticfiles import StaticFiles
    app.mount("/chat", StaticFiles(directory=_web_dir, html=True), name="web_chat")

if __name__ == "__main__":
    logger.info("Iniciando servidor en puerto 8080")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)