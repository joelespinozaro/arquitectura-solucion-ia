"""Compara los resultados de Locust (CSV) con loadtest/slo.yaml. Sale con código 1 si no se cumple.

Uso:  python check_slo.py resultados_stats.csv
"""
import csv
import sys
from pathlib import Path

import yaml


def evaluar(csv_path: str, slo_path: str = None) -> tuple[bool, str]:
    slo = yaml.safe_load(Path(slo_path or Path(__file__).with_name("slo.yaml")).read_text(encoding="utf-8"))
    with open(csv_path, newline="", encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f) if r["Name"] == "Aggregated"]
    if not filas:
        return False, "El CSV no tiene la fila 'Aggregated'. ¿Corriste Locust con --csv?"
    fila = filas[0]
    total = int(fila["Request Count"])
    if total == 0:
        return False, "No hubo peticiones."
    fallas = int(fila["Failure Count"])
    p50, p95, p99 = float(fila["50%"]), float(fila["95%"]), float(fila["99%"])
    tasa = 100 * fallas / total
    ok_lat = p95 <= slo["p95_ms"]
    ok_err = tasa <= slo["error_rate_pct"]
    msg = (
        f"Peticiones: {total}  |  p50 {p50:.0f} ms  p95 {p95:.0f} ms  p99 {p99:.0f} ms  |  errores {tasa:.2f}%\n"
        f"SLO latencia (p95 <= {slo['p95_ms']} ms): {'CUMPLE' if ok_lat else 'NO CUMPLE'}\n"
        f"SLO errores (<= {slo['error_rate_pct']}%): {'CUMPLE' if ok_err else 'NO CUMPLE'}"
    )
    return ok_lat and ok_err, msg


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python check_slo.py resultados_stats.csv")
    ok, msg = evaluar(sys.argv[1])
    print(msg)
    sys.exit(0 if ok else 1)
