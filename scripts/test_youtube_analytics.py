"""
Pequeño script para solicitar métricas de YouTube Analytics usando las credenciales activas.

Ejemplo:

    python scripts/test_youtube_analytics.py --start-date 2026-01-01 --end-date 2026-01-31 --max-results 20

La salida muestra primero los videos largos y luego los shorts, con los primeros grupos de filas.
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.youtube_api import obtener_analitica_videos_y_shorts


def _parse_metrics(value: str | None) -> Sequence[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def main() -> None:
    parser = ArgumentParser(description="Prueba rápida de YouTube Analytics (videos vs shorts).")
    parser.add_argument("--start-date", help="Fecha inicial (YYYY-MM-DD). Por defecto 30 días atrás.")
    parser.add_argument("--end-date", help="Fecha final (YYYY-MM-DD). Por defecto hoy.")
    parser.add_argument("--metrics", help="Métricas CSV (por ejemplo views,estimatedMinutesWatched).")
    parser.add_argument("--max-results", type=int, default=25, help="Cantidad máxima de videos a consultar.")
    parser.add_argument("--sample", type=int, default=5, help="Cuántos videos mostrar por categoría.")
    parser.add_argument("--filters", help="Filtros de YouTube Analytics (ver doc oficial).")
    args = parser.parse_args()

    rows = obtener_analitica_videos_y_shorts(
        start_date=args.start_date,
        end_date=args.end_date,
        metrics=tuple(_parse_metrics(args.metrics) or []),
        max_results=max(1, args.max_results),
        filters=args.filters,
        log_fn=print,
    )
    print(f"\nResultados YouTube Analytics ({len(rows['all'])} videos totales):")

    def _dump(section: str, entries: Sequence[dict]) -> None:
        limit = min(len(entries), args.sample)
        print(f"\n== {section} ({len(entries)}) {'' if limit == len(entries) else f'mostrando {limit}'} ==")
        for row in entries[:limit]:
            title = row.get("video_title") or row.get("video", "sin título")
            vid = row.get("video_id") or "<sin ID>"
            views = row.get("views") or row.get("metricValues") or ""
            duration = row.get("duration_seconds")
            print(f"- {title} [{vid}] views={views} duration={duration}")

    _dump("Videos largos", rows["videos"])
    _dump("Shorts", rows["shorts"])


if __name__ == "__main__":
    main()
