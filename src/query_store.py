from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import re

import pandas as pd


# Define aquí tus consultas SQL reutilizables
# Healthcheck: valida conexión y existencia de vistas/tablas esperadas en la DB activa.
Q_HEALTHCHECK = """
SELECT
    req.object_name,
    CASE WHEN t.TABLE_NAME IS NULL THEN 0 ELSE 1 END AS exists_in_db,
    t.TABLE_TYPE AS object_type,
    DATABASE() AS database_name
FROM (
    SELECT 'comandas_v6' AS object_name
    UNION ALL SELECT 'comandas_v6_todas'
    UNION ALL SELECT 'comandas_v6_base'
) req
LEFT JOIN information_schema.TABLES t
    ON t.TABLE_SCHEMA = DATABASE()
 AND t.TABLE_NAME = req.object_name;
"""

# Startup / modo operativo (ver docs/01-flujo_inicio_dashboard.md)
Q_STARTUP_ACTIVE_OPERATION = """
SELECT
    op.id AS id_operacion,
    op.estado_operacion AS estado_operacion_id,
    eop.nombre AS estado_operacion
FROM ope_operacion op
LEFT JOIN parameter_table eop
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
FROM ope_operacion op
LEFT JOIN parameter_table eop
    ON eop.id = op.estado_operacion
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE op.estado = 'HAB'
    AND op.estado_operacion = 23
ORDER BY op.id DESC
LIMIT 1;
"""

Q_STARTUP_HAS_REALTIME_ROWS = "SELECT 1 AS has_rows FROM comandas_v6 LIMIT 1;"


# Selector UI (ver docs/02-guia_dashboard_backstage.md, Apéndice A)
Q_LIST_OPERATIONS = """
SELECT
  op.id,
  op.fecha,
  op.nombre_operacion,
  op.estado_operacion,
  eop.nombre AS estado_operacion_nombre
FROM ope_operacion op
LEFT JOIN parameter_table eop
  ON eop.id = op.estado_operacion
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE op.estado = 'HAB'
ORDER BY op.id DESC
LIMIT 200;
"""


@dataclass(frozen=True)
class Filters:
    """Filtros para consultas del dashboard.

    Nota: en la fase inicial, usamos principalmente rangos por operativa.
    """

    op_ini: int | None = None
    op_fin: int | None = None
    dt_ini: str | None = None  # 'YYYY-MM-DD HH:MM:SS'
    dt_fin: str | None = None


def build_where(filters: Filters, mode: str) -> tuple[str, dict[str, Any]]:
    """Construye WHERE + params.

    mode:
      - 'ops'   -> filtra por id_operacion BETWEEN
      - 'dates' -> filtra por fecha_emision BETWEEN
      - 'none'  -> sin rango (solo tiempo real; la vista ya viene acotada)
    """

    clauses: list[str] = []
    params: dict[str, Any] = {}

    if mode == "ops":
        if filters.op_ini is None or filters.op_fin is None:
            raise ValueError("mode='ops' requiere op_ini y op_fin")
        clauses.append("id_operacion BETWEEN :op_ini AND :op_fin")
        params["op_ini"] = int(filters.op_ini)
        params["op_fin"] = int(filters.op_fin)
    elif mode == "dates":
        if filters.dt_ini is None or filters.dt_fin is None:
            raise ValueError("mode='dates' requiere dt_ini y dt_fin")
        clauses.append("fecha_emision BETWEEN :dt_ini AND :dt_fin")
        params["dt_ini"] = filters.dt_ini
        params["dt_fin"] = filters.dt_fin
    elif mode == "none":
        pass
    else:
        raise ValueError("mode inválido: use 'ops'|'dates'|'none'")

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    return where_sql, params


_SQLA_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def _to_mysqlconnector_paramstyle(query: str) -> str:
    """Convierte placeholders SQLAlchemy (:name) a mysql-connector (%(name)s)."""

    return _SQLA_PARAM_RE.sub(r"%(\1)s", query)


def q_kpis(view_name: str, where_sql: str) -> str:
    return f"""
    SELECT
      COALESCE(SUM(sub_total), 0) AS total_vendido,
      COUNT(DISTINCT id_comanda)  AS total_comandas,
      COALESCE(SUM(cantidad), 0)  AS items_vendidos,
      ROUND(COALESCE(SUM(sub_total), 0) / NULLIF(COUNT(DISTINCT id_comanda), 0), 2) AS ticket_promedio
    FROM {view_name}
    {where_sql};
    """


def q_estado_operativo(view_name: str, where_sql: str) -> str:
        return f"""
        SELECT
            COUNT(DISTINCT CASE WHEN estado_comanda = 'PENDIENTE' THEN id_comanda END) AS comandas_pendientes,
            COUNT(
                DISTINCT CASE
                    WHEN (estado_impresion IS NULL OR estado_impresion <> 'IMPRESO') THEN id_comanda
                END
            ) AS comandas_no_impresas
        FROM {view_name}
        {where_sql};
        """


def _append_condition(where_sql: str, condition_sql: str) -> str:
        if where_sql.strip():
                return f"{where_sql} AND {condition_sql}"
        return f"WHERE {condition_sql}"


def q_ids_comandas_pendientes(view_name: str, where_sql: str, limit: int = 50) -> str:
        where2 = _append_condition(where_sql, "estado_comanda = 'PENDIENTE'")
        return f"""
        SELECT DISTINCT
            id_comanda
        FROM {view_name}
        {where2}
        ORDER BY id_comanda DESC
        LIMIT {int(limit)};
        """


def q_ids_comandas_no_impresas(view_name: str, where_sql: str, limit: int = 50) -> str:
        where2 = _append_condition(where_sql, "(estado_impresion IS NULL OR estado_impresion <> 'IMPRESO')")
        return f"""
        SELECT DISTINCT
            id_comanda
        FROM {view_name}
        {where2}
        ORDER BY id_comanda DESC
        LIMIT {int(limit)};
        """


def q_ventas_por_hora(view_name: str, where_sql: str) -> str:
        return f"""
        SELECT
            HOUR(fecha_emision) AS hora,
            COALESCE(SUM(sub_total), 0) AS total_vendido,
            COUNT(DISTINCT id_comanda) AS comandas,
            COALESCE(SUM(cantidad), 0) AS items
        FROM {view_name}
        {where_sql}
        GROUP BY HOUR(fecha_emision)
        ORDER BY hora;
        """


def q_por_categoria(view_name: str, where_sql: str) -> str:
        return f"""
        SELECT
            COALESCE(categoria, 'SIN CATEGORIA') AS categoria,
            COALESCE(SUM(sub_total), 0) AS total_vendido,
            COALESCE(SUM(cantidad), 0)  AS unidades,
            COUNT(DISTINCT id_comanda)  AS comandas
        FROM {view_name}
        {where_sql}
        GROUP BY COALESCE(categoria, 'SIN CATEGORIA')
        ORDER BY total_vendido DESC;
        """


def q_top_productos(view_name: str, where_sql: str, limit: int = 20) -> str:
        return f"""
        SELECT
            nombre,
            COALESCE(categoria, 'SIN CATEGORIA') AS categoria,
            COALESCE(SUM(cantidad), 0) AS unidades,
            COALESCE(SUM(sub_total), 0) AS total_vendido
        FROM {view_name}
        {where_sql}
        GROUP BY nombre, COALESCE(categoria, 'SIN CATEGORIA')
        ORDER BY total_vendido DESC
        LIMIT {int(limit)};
        """


def q_por_usuario(view_name: str, where_sql: str, limit: int = 20) -> str:
        return f"""
        SELECT
            COALESCE(usuario_reg, 'SIN USUARIO') AS usuario_reg,
            COALESCE(SUM(sub_total), 0) AS total_vendido,
            COUNT(DISTINCT id_comanda)  AS comandas,
            COALESCE(SUM(cantidad), 0)  AS items,
            ROUND(COALESCE(SUM(sub_total), 0) / NULLIF(COUNT(DISTINCT id_comanda), 0), 2) AS ticket_promedio
        FROM {view_name}
        {where_sql}
        GROUP BY COALESCE(usuario_reg, 'SIN USUARIO')
        ORDER BY total_vendido DESC
        LIMIT {int(limit)};
        """


def q_detalle(view_name: str, where_sql: str, limit: int = 500) -> str:
        return f"""
        SELECT
            fecha_emision,
            id_operacion,
            id_comanda,
            id_mesa,
            usuario_reg,
            nombre,
            COALESCE(categoria, 'SIN CATEGORIA') AS categoria,
            cantidad,
            precio_venta,
            sub_total,
            tipo_salida,
            estado_comanda,
            estado_impresion,
            id_factura,
            nro_factura
        FROM {view_name}
        {where_sql}
        ORDER BY fecha_emision DESC
        LIMIT {int(limit)};
        """


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

    query = _to_mysqlconnector_paramstyle(query)

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or {})
        rows: Iterable[dict[str, Any]] = cursor.fetchall()
        return pd.DataFrame(list(rows))
    finally:
        cursor.close()
