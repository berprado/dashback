from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


# Define aquí tus consultas SQL reutilizables
Q_HEALTHCHECK = "SELECT 1 AS ok"  # útil para probar conexión


def fetch_dataframe(conn, query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve el resultado como DataFrame."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or {})
        rows: Iterable[dict[str, Any]] = cursor.fetchall()
        return pd.DataFrame(list(rows))
    finally:
        cursor.close()
