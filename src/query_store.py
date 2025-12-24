from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


# Define aquí tus consultas SQL reutilizables
Q_HEALTHCHECK = "SELECT 1 AS ok"  # útil para probar conexión

# Startup / modo operativo (ver docs/01-flujo_inicio_dashboard.md)
Q_STARTUP_ACTIVE_OPERATION = """
SELECT
    op.id AS id_operacion,
    op.estado_operacion AS estado_operacion_id,
    eop.nombre AS estado_operacion
FROM adminerp_copy.ope_operacion op
LEFT JOIN adminerp_copy.parameter_table eop
    ON eop.id = op.estado_operacion
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE op.estado = 'HAB'
    AND op.estado_operacion IN (22, 24)
ORDER BY op.id DESC
LIMIT 1;
"""

Q_STARTUP_LAST_CLOSED_OPERATION = """
SELECT
    op.id AS id_operacion,
    op.estado_operacion AS estado_operacion_id,
    eop.nombre AS estado_operacion
FROM adminerp_copy.ope_operacion op
LEFT JOIN adminerp_copy.parameter_table eop
    ON eop.id = op.estado_operacion
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE op.estado = 'HAB'
    AND op.estado_operacion = 23
ORDER BY op.id DESC
LIMIT 1;
"""

Q_STARTUP_HAS_REALTIME_ROWS = "SELECT 1 AS has_rows FROM adminerp_copy.comandas_v6 LIMIT 1;"


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
