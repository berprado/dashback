from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


# Define aquí tus consultas SQL reutilizables
Q_HEALTHCHECK = "SELECT 1 AS ok"  # útil para probar conexión


def fetch_dataframe(conn: Any, query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve el resultado como DataFrame.

    Soporta:
    - `streamlit.connections.sql_connection.SQLConnection` (usa `conn.query`).
    - `mysql.connector` (usa cursor `dictionary=True`).
    """

    if hasattr(conn, "query"):
        try:
            return conn.query(query, params=params or {}, ttl=0)
        except TypeError:
            return conn.query(query, params=params or {})

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or {})
        rows: Iterable[dict[str, Any]] = cursor.fetchall()
        return pd.DataFrame(list(rows))
    finally:
        cursor.close()
