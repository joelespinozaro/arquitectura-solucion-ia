"""Pasa a un dataset de LangSmith las respuestas que un usuario marcó como malas.

Uso (desde 02_agent_api, con el .env cargado):
    python -I scripts/to_dataset.py --limite 20
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repositories import SessionLocal  # noqa: E402
from src.repositories.history_repository import HistoryRepository  # noqa: E402
from src.services.eval_service import DATASET_ERRORES, pasar_negativos_a_dataset  # noqa: E402
from src.utils.observability import langsmith_activo  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=20)
    ap.add_argument("--dataset", default=DATASET_ERRORES)
    args = ap.parse_args()

    if not langsmith_activo():
        sys.exit("Activa LANGSMITH_TRACING=true y pon LANGSMITH_API_KEY en el .env")

    db = SessionLocal()
    try:
        negativos = HistoryRepository(db).get_negative(limit=args.limite)
        n = pasar_negativos_a_dataset(negativos, nombre=args.dataset)
    finally:
        db.close()
    print(f"{n} caso(s) guardados en el dataset '{args.dataset}'")


if __name__ == "__main__":
    main()
