"""Juez automático sobre tráfico real (M5S2 parte 2).

Lee las conversaciones recientes de la base, le pide a un modelo que decida si cada
respuesta se apoya en su contexto y adjunta el resultado (`grounded`, 1 o 0) a la
traza de LangSmith.

Uso (desde 02_agent_api, con el .env cargado):
    python -I scripts/judge_traces.py --horas 24 --limite 10
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from src.repositories import SessionLocal  # noqa: E402
from src.repositories.history_repository import HistoryRepository  # noqa: E402
from src.services.eval_service import juzgar_conversaciones  # noqa: E402
from src.utils.llm_factory import build_chat_model  # noqa: E402
from src.utils.observability import langsmith_activo  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=int, default=24)
    ap.add_argument("--limite", type=int, default=10)
    args = ap.parse_args()

    if not langsmith_activo():
        sys.exit("Activa LANGSMITH_TRACING=true y pon LANGSMITH_API_KEY en el .env")

    db = SessionLocal()
    try:
        historial = HistoryRepository(db).get_recent(hours=args.horas, limit=args.limite)
        print(f"Conversaciones a juzgar: {len(historial)}")
        llm = build_chat_model(temperature=0)
        r = juzgar_conversaciones(llm, historial)
    finally:
        db.close()

    for trace_id, score, razon in r["detalle"]:
        print(f"  {trace_id[:8]}  grounded={int(score)}  {razon}")
    print(f"Resumen: {r['ok']} bien, {r['inventadas']} con datos inventados, "
          f"{r['sin_veredicto']} sin veredicto, {r['no_enviadas']} sin enviar a LangSmith")


if __name__ == "__main__":
    main()
