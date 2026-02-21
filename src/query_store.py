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
    req.category,
    CASE WHEN t.TABLE_NAME IS NULL THEN 0 ELSE 1 END AS exists_in_db,
    t.TABLE_TYPE AS object_type,
    DATABASE() AS database_name
FROM (
    SELECT 'comandas_v6' AS object_name, 'core' AS category
    UNION ALL SELECT 'comandas_v6_todas', 'core'
    UNION ALL SELECT 'comandas_v6_base', 'core'
    UNION ALL SELECT 'comandas_v7', 'diagnostico'
    UNION ALL SELECT 'vw_comanda_ultima_impresion', 'diagnostico'
    UNION ALL SELECT 'bar_comanda_impresion', 'diagnostico'
    UNION ALL SELECT 'vw_margen_comanda', 'pnl'
    UNION ALL SELECT 'vw_consumo_valorizado_operativa', 'pnl'
    UNION ALL SELECT 'vw_consumo_insumos_operativa', 'pnl'
    UNION ALL SELECT 'vw_cogs_comanda', 'pnl'
) req
LEFT JOIN information_schema.TABLES t
    ON t.TABLE_SCHEMA = DATABASE()
 AND t.TABLE_NAME = req.object_name
ORDER BY req.category, req.object_name;
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


def build_where(
    filters: Filters,
    mode: str,
    *,
    table_alias: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Construye WHERE + params.

    mode:
      - 'ops'   -> filtra por id_operacion BETWEEN
      - 'dates' -> filtra por fecha_emision BETWEEN
      - 'none'  -> sin rango (solo tiempo real; la vista ya viene acotada)
    """

    clauses: list[str] = []
    params: dict[str, Any] = {}

    def _col(name: str) -> str:
        return f"{table_alias}.{name}" if table_alias else name

    if mode == "ops":
        if filters.op_ini is None or filters.op_fin is None:
            raise ValueError("mode='ops' requiere op_ini y op_fin")
        clauses.append(f"{_col('id_operacion')} BETWEEN :op_ini AND :op_fin")
        params["op_ini"] = int(filters.op_ini)
        params["op_fin"] = int(filters.op_fin)
    elif mode == "dates":
        if filters.dt_ini is None or filters.dt_fin is None:
            raise ValueError("mode='dates' requiere dt_ini y dt_fin")
        clauses.append(f"{_col('fecha_emision')} BETWEEN :dt_ini AND :dt_fin")
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


def _cond_venta_final(table_alias: str | None = None) -> str:
    """Condición de venta finalizada (criterio estricto por vista).

    Regla:
    - tipo_salida = VENTA
    - estado_comanda = PROCESADO
    - estado_impresion = IMPRESO
    """

    p = f"{table_alias}." if table_alias else ""
    return (
        f"UPPER(COALESCE({p}tipo_salida, '')) = 'VENTA' "
        f"AND {p}estado_comanda = 'PROCESADO' "
        f"AND {p}estado_impresion = 'IMPRESO'"
    )


def _cond_cortesia_final(table_alias: str | None = None) -> str:
    """Condición de cortesía finalizada (criterio estricto por vista)."""

    p = f"{table_alias}." if table_alias else ""
    return (
        f"UPPER(COALESCE({p}tipo_salida, '')) = 'CORTESIA' "
        f"AND {p}estado_comanda = 'PROCESADO' "
        f"AND {p}estado_impresion = 'IMPRESO'"
    )


def q_kpis(view_name: str, where_sql: str) -> str:
    cond_venta = _cond_venta_final("v")
    cond_cortesia = _cond_cortesia_final("v")

    # Variante "efectiva" para ventas finalizadas, usando el log como señal alternativa.
    cond_venta_impreso_log = _cond_venta_final_impreso_log()

    return f"""
    SELECT
            COALESCE(SUM(CASE WHEN {cond_venta} THEN v.sub_total ELSE 0 END), 0) AS total_vendido,
            COUNT(DISTINCT CASE WHEN {cond_venta} THEN v.id_comanda END)  AS total_comandas,
            COALESCE(SUM(CASE WHEN {cond_venta} THEN v.cantidad ELSE 0 END), 0)  AS items_vendidos,
            ROUND(
                COALESCE(SUM(CASE WHEN {cond_venta} THEN v.sub_total ELSE 0 END), 0)
                / NULLIF(COUNT(DISTINCT CASE WHEN {cond_venta} THEN v.id_comanda END), 0),
                2
            ) AS ticket_promedio

            ,COALESCE(
                SUM(CASE WHEN {cond_venta_impreso_log} THEN v.sub_total ELSE 0 END),
                0
            ) AS total_vendido_impreso_log

            ,COUNT(
                DISTINCT CASE
                    WHEN {cond_venta_impreso_log} THEN v.id_comanda
                END
            ) AS total_comandas_impreso_log

            ,COALESCE(
                SUM(CASE WHEN {cond_venta_impreso_log} THEN v.cantidad ELSE 0 END),
                0
            ) AS items_vendidos_impreso_log

            ,ROUND(
                COALESCE(
                    SUM(CASE WHEN {cond_venta_impreso_log} THEN v.sub_total ELSE 0 END),
                    0
                )
                / NULLIF(
                    COUNT(
                        DISTINCT CASE
                            WHEN {cond_venta_impreso_log} THEN v.id_comanda
                        END
                    ),
                    0
                ),
                2
            ) AS ticket_promedio_impreso_log

            ,COALESCE(
                SUM(
                    CASE
                        WHEN {cond_cortesia}
                            THEN COALESCE(v.cor_subtotal_anterior, v.sub_total, 0)
                        ELSE 0
                    END
                ),
                0
            ) AS total_cortesia

            ,COUNT(
                DISTINCT CASE
                    WHEN {cond_cortesia} THEN v.id_comanda
                END
            ) AS comandas_cortesia

            ,COALESCE(
                SUM(
                    CASE WHEN {cond_cortesia} THEN v.cantidad ELSE 0 END
                ),
                0
            ) AS items_cortesia
    FROM {view_name} v
    {_join_impresion_log(table_alias="v")}
    {where_sql};
    """


def _cond_venta_final_impreso_log() -> str:
    """Condición 'efectiva' de venta finalizada usando log de impresión.

    Se interpreta como finalizada si:
    - es venta y está PROCESADO
    - y (la vista marca IMPRESO o el último log marca IMPRESO)

    Requiere que el query tenga alias `v` para la vista y `ei_log` para el nombre del estado desde log.
    """

    return (
        "UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA' "
        "AND v.estado_comanda = 'PROCESADO' "
        "AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')"
    )


def _join_impresion_log(*, table_alias: str = "v") -> str:
    """JOIN al log de impresión para señal alternativa de IMPRESO."""

    return f"""
    LEFT JOIN vw_comanda_ultima_impresion imp
        ON imp.id_comanda = {table_alias}.id_comanda
    LEFT JOIN parameter_table ei_log
        ON ei_log.id = imp.ind_estado_impresion
       AND ei_log.id_master = 10
       AND ei_log.estado = 'HAB'
    """


def q_estado_operativo(view_name: str, where_sql: str) -> str:
        return f"""
        SELECT
            COUNT(DISTINCT CASE WHEN estado_comanda = 'PENDIENTE' THEN id_comanda END) AS comandas_pendientes,
            COUNT(DISTINCT CASE WHEN estado_comanda = 'ANULADO' THEN id_comanda END) AS comandas_anuladas,
            COUNT(
                DISTINCT CASE
                    WHEN estado_comanda <> 'ANULADO' AND estado_impresion = 'PENDIENTE' THEN id_comanda
                END
            ) AS comandas_impresion_pendiente,
            COUNT(
                DISTINCT CASE
                    WHEN estado_comanda <> 'ANULADO' AND estado_impresion IS NULL THEN id_comanda
                END
            ) AS comandas_sin_estado_impresion
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
    where2 = _append_condition(
        where_sql,
        "estado_comanda <> 'ANULADO' AND (estado_impresion IS NULL OR estado_impresion = 'PENDIENTE')",
    )
    return f"""
    SELECT DISTINCT
        id_comanda
    FROM {view_name}
    {where2}
    ORDER BY id_comanda DESC
    LIMIT {int(limit)};
    """


def q_ids_comandas_impresion_pendiente(view_name: str, where_sql: str, limit: int = 50) -> str:
    where2 = _append_condition(
        where_sql,
        "estado_comanda <> 'ANULADO' AND estado_impresion = 'PENDIENTE'",
    )
    return f"""
    SELECT DISTINCT
        id_comanda
    FROM {view_name}
    {where2}
    ORDER BY id_comanda DESC
    LIMIT {int(limit)};
    """


def q_ids_comandas_sin_estado_impresion(view_name: str, where_sql: str, limit: int = 50) -> str:
    where2 = _append_condition(
        where_sql,
        "estado_comanda <> 'ANULADO' AND estado_impresion IS NULL",
    )
    return f"""
    SELECT DISTINCT
        id_comanda
    FROM {view_name}
    {where2}
    ORDER BY id_comanda DESC
    LIMIT {int(limit)};
    """


def q_ids_comandas_anuladas(view_name: str, where_sql: str, limit: int = 50) -> str:
		where2 = _append_condition(where_sql, "estado_comanda = 'ANULADO'")
		return f"""
		SELECT DISTINCT
			id_comanda
		FROM {view_name}
		{where2}
		ORDER BY id_comanda DESC
		LIMIT {int(limit)};
		"""


def q_ventas_por_hora(view_name: str, where_sql: str, *, use_impresion_log: bool = False) -> str:
    cond = _cond_venta_final("v") if not use_impresion_log else _cond_venta_final_impreso_log()
    where2 = _append_condition(where_sql, cond)

    join_sql = _join_impresion_log(table_alias="v") if use_impresion_log else ""

    return f"""
        SELECT
            HOUR(v.fecha_emision) AS hora,
            COALESCE(SUM(v.sub_total), 0) AS total_vendido,
            COUNT(DISTINCT v.id_comanda) AS comandas,
            COALESCE(SUM(v.cantidad), 0) AS items
        FROM {view_name} v
        {join_sql}
        {where2}
        GROUP BY HOUR(v.fecha_emision)
        ORDER BY hora;
        """


def q_por_categoria(view_name: str, where_sql: str, *, use_impresion_log: bool = False) -> str:
    cond = _cond_venta_final("v") if not use_impresion_log else _cond_venta_final_impreso_log()
    where2 = _append_condition(where_sql, cond)

    join_sql = _join_impresion_log(table_alias="v") if use_impresion_log else ""

    return f"""
        SELECT
            COALESCE(v.categoria, 'SIN CATEGORIA') AS categoria,
            COALESCE(SUM(v.sub_total), 0) AS total_vendido,
            COALESCE(SUM(v.cantidad), 0)  AS unidades,
            COUNT(DISTINCT v.id_comanda)  AS comandas
        FROM {view_name} v
        {join_sql}
        {where2}
        GROUP BY COALESCE(v.categoria, 'SIN CATEGORIA')
        ORDER BY total_vendido DESC;
        """


def q_top_productos(
    view_name: str,
    where_sql: str,
    limit: int = 20,
    *,
    use_impresion_log: bool = False,
) -> str:
    cond = _cond_venta_final("v") if not use_impresion_log else _cond_venta_final_impreso_log()
    where2 = _append_condition(where_sql, cond)

    join_sql = _join_impresion_log(table_alias="v") if use_impresion_log else ""

    return f"""
        SELECT
            v.nombre,
            COALESCE(v.categoria, 'SIN CATEGORIA') AS categoria,
            COALESCE(SUM(v.cantidad), 0) AS unidades,
            COALESCE(SUM(v.sub_total), 0) AS total_vendido
        FROM {view_name} v
        {join_sql}
        {where2}
        GROUP BY v.nombre, COALESCE(v.categoria, 'SIN CATEGORIA')
        ORDER BY total_vendido DESC
        LIMIT {int(limit)};
        """


def q_por_usuario(view_name: str, where_sql: str, limit: int = 20, *, use_impresion_log: bool = False) -> str:
    cond = _cond_venta_final("v") if not use_impresion_log else _cond_venta_final_impreso_log()
    where2 = _append_condition(where_sql, cond)

    join_sql = _join_impresion_log(table_alias="v") if use_impresion_log else ""

    return f"""
        SELECT
            COALESCE(v.usuario_reg, 'SIN USUARIO') AS usuario_reg,
            COALESCE(SUM(v.sub_total), 0) AS total_vendido,
            COUNT(DISTINCT v.id_comanda)  AS comandas,
            COALESCE(SUM(v.cantidad), 0)  AS items,
            ROUND(COALESCE(SUM(v.sub_total), 0) / NULLIF(COUNT(DISTINCT v.id_comanda), 0), 2) AS ticket_promedio
        FROM {view_name} v
        {join_sql}
        {where2}
        GROUP BY COALESCE(v.usuario_reg, 'SIN USUARIO')
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


def q_comandas_emision_times(view_name: str, where_sql: str, *, limit: int | None = None) -> str:
        """Timestamps de emisión por comanda (una fila por id_comanda).

        Nota: la vista contiene múltiples filas por comanda (ítems). Para medir cadencia de emisión,
        necesitamos un timestamp único por comanda; se usa MIN(fecha_emision) por id_comanda.

        - Si `limit` es None: devuelve todas las comandas del rango/operativa.
        - Si `limit` está definido: devuelve las últimas N comandas (por fecha_emision desc).
        """

        if limit is None:
                return f"""
                SELECT
                    id_comanda,
                    MIN(fecha_emision) AS fecha_emision
                FROM {view_name}
                {where_sql}
                GROUP BY id_comanda
                ORDER BY fecha_emision ASC;
                """

        return f"""
        SELECT
            id_comanda,
            fecha_emision
        FROM (
            SELECT
                id_comanda,
                MIN(fecha_emision) AS fecha_emision
            FROM {view_name}
            {where_sql}
            GROUP BY id_comanda
            ORDER BY fecha_emision DESC
            LIMIT {int(limit)}
        ) t
        ORDER BY fecha_emision ASC;
        """


def q_impresion_snapshot(view_name: str, ids: list[int]) -> str:
    """Snapshot de estados de impresión para depuración.

    Compara tres señales:
    - `estado_impresion` tal como lo entrega la vista del dashboard (v6/v6_todas).
    - `bar_comanda.estado_impresion` (ID) + su nombre (parameter_table id_master=10).
    - último registro de impresión (vw_comanda_ultima_impresion) + su nombre.

    Nota: `ids` se incrusta como lista de enteros (sanitizados) para permitir IN (...)
    sin pelear con la parametrización de listas en MySQL/SQLAlchemy.
    """

    safe_ids = [int(x) for x in ids if x is not None]
    if not safe_ids:
        return "SELECT NULL AS id_comanda WHERE 1=0;"

    ids_sql = ", ".join(map(str, safe_ids))

    return f"""
    SELECT
        t.id_comanda,
        t.id_operacion,
        t.fecha_emision_ult,
        t.estado_comanda AS estado_comanda_vista,
        t.estado_impresion AS estado_impresion_vista,

        CASE WHEN bc.id IS NULL THEN 0 ELSE 1 END AS exists_en_bar_comanda,

        bc.estado_impresion AS estado_impresion_id_bar_comanda,
        pti.nombre AS estado_impresion_bar_comanda,

        CASE WHEN vui.id_comanda IS NULL THEN 0 ELSE 1 END AS exists_en_log_impresion,

        vui.ind_estado_impresion AS estado_impresion_id_log,
        pti2.nombre AS estado_impresion_log
    FROM (
        SELECT
            id_comanda,
            MAX(id_operacion) AS id_operacion,
            MAX(fecha_emision) AS fecha_emision_ult,
            MAX(estado_comanda) AS estado_comanda,
            MAX(estado_impresion) AS estado_impresion
        FROM {view_name}
        WHERE id_comanda IN ({ids_sql})
        GROUP BY id_comanda
    ) t
    LEFT JOIN bar_comanda bc
        ON bc.id = t.id_comanda
    LEFT JOIN parameter_table pti
        ON pti.id = bc.estado_impresion
       AND pti.id_master = 10
       AND pti.estado = 'HAB'
    LEFT JOIN vw_comanda_ultima_impresion vui
        ON vui.id_comanda = t.id_comanda
    LEFT JOIN parameter_table pti2
        ON pti2.id = vui.ind_estado_impresion
       AND pti2.id_master = 10
       AND pti2.estado = 'HAB'
    ORDER BY t.id_comanda DESC;
    """


def fetch_dataframe(
    conn: Any,
    query: str,
    params: dict[str, Any] | None = None,
    *,
    ttl: int | None = None,
) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve el resultado como DataFrame.

    Soporta:
    - `streamlit.connections.sql_connection.SQLConnection` (usa `conn.query`).
    - `mysql.connector` (usa cursor `dictionary=True`).
    """

    if hasattr(conn, "query"):
        try:
            if ttl is None:
                return conn.query(query, params=params or {})
            return conn.query(query, params=params or {}, ttl=ttl)
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

# ===== WAC / COGS / MÁRGENES =====

def q_wac_cogs_summary(view_name: str, where_sql: str) -> str:
    """P&L consolidado de la operativa (ventas, COGS, margen).
	
    Ejecutivo: lo que mira el dueño.
    - Ventas: suma total facturado (tipo_salida='VENTA' finalizado)
    - COGS: suma costo insumos consumidos
    - Margen: utilidad bruta = ventas - cogs
	
    Base para:
    - Dashboard financiero
    - Margen por día/operativa
    - Control de rentabilidad global
	
    Supuesto: vw_margen_comanda ya existe en la BD con columnas:
    - total_venta, cogs_comanda, margen_comanda
    - id_operacion (y/o fecha_emision si se usa filtro por fechas)
    """
	
    return f"""
    SELECT
        COALESCE(SUM(total_venta), 0) AS total_ventas,
        COALESCE(SUM(cogs_comanda), 0) AS total_cogs,
        COALESCE(SUM(margen_comanda), 0) AS total_margen,
        ROUND(
            COALESCE(SUM(margen_comanda), 0) / NULLIF(COALESCE(SUM(total_venta), 0), 0) * 100,
            2
        ) AS margen_pct
    FROM {view_name} v
    {where_sql};
    """


def q_wac_cogs_detalle(view_name: str, where_sql: str, *, limit: int) -> str:
    """Detalle P&L por comanda.

    Retorna una fila por comanda con venta, COGS, margen e información contextual.
    Incluye mesa, usuario y estado para mejor auditoría (via JOIN a bar_comanda).
    """

    return f"""
    SELECT
        v.id_operacion,
        v.id_comanda,
        bc.id_mesa,
        bc.usuario_reg,
        bc.fecha AS fecha_emision,
        bc.estado_comanda,
        v.id_barra,
        v.total_venta,
        v.cogs_comanda,
        v.margen_comanda
    FROM {view_name} v
    LEFT JOIN bar_comanda bc ON bc.id = v.id_comanda
    {where_sql}
    ORDER BY v.id_comanda DESC
    LIMIT :limit;
    """


def q_consumo_valorizado(view_name: str, where_sql: str, *, limit: int) -> str:
    """Consumo valorizado de insumos por producto.

    Muestra qué insumos se consumieron, con cantidad, WAC y costo total.
    Consulta logística para conciliación de inventario y detección de mermas.
    """

    return f"""
    SELECT
        v.id_operacion,
        v.id_producto,
        p.nombre AS nombre_producto,
        v.cantidad_consumida_base,
        v.wac_operativa,
        v.costo_consumo
    FROM {view_name} v
    LEFT JOIN alm_producto p
        ON p.id = v.id_producto
       AND p.estado = 'HAB'
    {where_sql}
    ORDER BY v.costo_consumo DESC
    LIMIT :limit;
    """


def q_consumo_sin_valorar(view_name: str, where_sql: str, *, limit: int) -> str:
    """Consumo sin valorar (sanidad de cantidades).

    Aísla el problema de cantidades del problema de costos.
    Si algo está mal aquí: no es WAC, no es margen, es receta/multiplicación/unidades.
    Regla de oro: si el consumo está mal, todo lo demás estará mal aunque el WAC sea perfecto.
    """

    return f"""
    SELECT
        v.id_operacion,
        v.id_producto,
        p.nombre AS nombre_producto,
        v.cantidad_consumida_base
    FROM {view_name} v
    LEFT JOIN alm_producto p
        ON p.id = v.id_producto
       AND p.estado = 'HAB'
    {where_sql}
    ORDER BY v.cantidad_consumida_base DESC
    LIMIT :limit;
    """


def q_cogs_por_comanda(view_name: str, where_sql: str, *, limit: int) -> str:
    """COGS por comanda (sin ventas).

    Ver solo el costo, sin precio de venta.
    Ideal para cortesías (tienen COGS pero no ventas) y auditoría de consumo puro.
    Incluye mesa, usuario y estado para contexto (via JOIN a bar_comanda).
    """

    return f"""
    SELECT
        v.id_operacion,
        v.id_comanda,
        bc.id_mesa,
        bc.usuario_reg,
        bc.fecha AS fecha_emision,
        bc.estado_comanda,
        v.id_barra,
        v.cogs_comanda
    FROM {view_name} v
    LEFT JOIN bar_comanda bc ON bc.id = v.id_comanda
    {where_sql}
    ORDER BY v.cogs_comanda DESC
    LIMIT :limit;
    """


def q_pour_cost_por_combo(view_name: str, where_sql: str, *, limit: int) -> str:
    """Pour cost por combo (prorrateo de COGS por proporción de venta).

    Estrategia:
    1. Agrupa ventas por combo (nombre) dentro de cada comanda.
    2. Obtiene COGS total de la comanda desde `vw_cogs_comanda`.
    3. Prorratea el COGS según la proporción de ventas de cada combo.
    
    Fórmula: cogs_asignado = cogs_total_comanda * (ventas_combo / ventas_total_comanda)
    """

    cond_venta = _cond_venta_final("v")
    where_venta = _append_condition(where_sql, cond_venta)
    
    cond_combo = "COALESCE(v.id_salida_combo_coctel, 0) <> 0"
    where_combo = _append_condition(where_venta, cond_combo)

    return f"""
    SELECT
        agg.nombre_combo,
        agg.cantidad_vendida,
        ROUND(agg.cogs_asignado / NULLIF(agg.cantidad_vendida, 0), 4) AS cogs_combo,
        agg.ventas_combo,
        ROUND(agg.cogs_asignado, 2) AS cogs_asignado,
        ROUND(agg.cogs_asignado / NULLIF(agg.ventas_combo, 0) * 100, 2) AS pour_cost_pct
    FROM (
        -- Agrupa por nombre de combo (globalmente) sumando todas las instancias
        SELECT
            x.nombre_combo,
            SUM(x.cantidad_vendida) AS cantidad_vendida,
            SUM(x.ventas_combo) AS ventas_combo,
            SUM(x.cogs_asignado) AS cogs_asignado
        FROM (
            -- Prorrateo por combo dentro de cada comanda
            SELECT
                combo_ventas.id_operacion,
                combo_ventas.id_comanda,
                combo_ventas.nombre_combo,
                combo_ventas.cantidad_vendida,
                combo_ventas.ventas_combo,
                COALESCE(cc.cogs_comanda, 0) * 
                    (combo_ventas.ventas_combo / NULLIF(comanda_totales.ventas_total, 0)) 
                AS cogs_asignado
            FROM (
                SELECT
                    v.id_operacion,
                    v.id_comanda,
                    COALESCE(v.nombre, 'SIN NOMBRE') AS nombre_combo,
                    SUM(v.cantidad) AS cantidad_vendida,
                    SUM(v.sub_total) AS ventas_combo
                FROM {view_name} v
                {where_combo}
                GROUP BY v.id_operacion, v.id_comanda, COALESCE(v.nombre, 'SIN NOMBRE')
            ) combo_ventas
            LEFT JOIN (
                SELECT
                    v.id_operacion,
                    v.id_comanda,
                    SUM(v.sub_total) AS ventas_total
                FROM {view_name} v
                {where_venta}
                GROUP BY v.id_operacion, v.id_comanda
            ) comanda_totales
                ON comanda_totales.id_operacion = combo_ventas.id_operacion
                AND comanda_totales.id_comanda = combo_ventas.id_comanda
            LEFT JOIN vw_cogs_comanda cc
                ON cc.id_operacion = combo_ventas.id_operacion
                AND cc.id_comanda = combo_ventas.id_comanda
                AND cc.id_barra = 1
        ) x
        WHERE x.ventas_combo > 0
        GROUP BY x.nombre_combo
    ) agg
    WHERE agg.ventas_combo > 0
    ORDER BY pour_cost_pct DESC, agg.ventas_combo DESC
    LIMIT :limit;
    """


def q_items_por_comanda(view_name: str, id_comanda: int) -> str:
    """Obtiene los ítems consumidos de una comanda específica.

    Usado para mostrar detalles en expandible: qué productos se consumieron,
    cantidades, precios unitarios y subtotales.
    """

    return f"""
    SELECT
        v.id_comanda,
        v.nombre AS nombre_producto,
        v.cantidad,
        v.precio_venta,
        v.sub_total,
        v.categoria
    FROM {view_name} v
    WHERE v.id_comanda = :id_comanda
    ORDER BY v.id ASC;
    """
