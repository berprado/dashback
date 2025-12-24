from __future__ import annotations

from typing import Any

from src.query_store import (
	Filters,
	build_where,
	fetch_dataframe,
	q_detalle,
	q_kpis,
	q_por_categoria,
	q_top_productos,
	q_ventas_por_hora,
)


class QueryExecutionError(RuntimeError):
	"""Error enriquecido para depurar consultas SQL.

	Se usa como "smoke check" opcional para mostrar el SQL y params
	que se intentaron ejecutar, sin exponer secretos.
	"""

	def __init__(
		self,
		message: str,
		*,
		sql: str,
		params: dict[str, Any],
		original_exc: Exception,
	) -> None:
		super().__init__(f"{message}: {original_exc}")
		self.sql = sql
		self.params = params
		self.original_exc = original_exc


def _run_df(conn: Any, sql: str, params: dict[str, Any], *, context: str):
	try:
		return fetch_dataframe(conn, sql, params)
	except Exception as exc:
		raise QueryExecutionError(context, sql=sql, params=params, original_exc=exc) from exc


def _to_float(value: Any) -> float:
	if value is None:
		return 0.0
	try:
		return float(value)
	except (TypeError, ValueError):
		return 0.0


def _to_int(value: Any) -> int:
	if value is None:
		return 0
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0


def get_kpis(conn: Any, view_name: str, filters: Filters, mode: str) -> dict[str, Any]:
	"""KPIs base del dashboard.

	- `mode='none'`: real-time (la vista ya viene acotada)
	- `mode='ops'|'dates'`: histórico con filtros
	"""

	where_sql, params = build_where(filters, mode)
	sql = q_kpis(view_name, where_sql)
	df = _run_df(conn, sql, params, context="Error ejecutando KPIs")

	if df is None or df.empty:
		return {
			"total_vendido": 0.0,
			"total_comandas": 0,
			"items_vendidos": 0.0,
			"ticket_promedio": 0.0,
		}

	row = df.iloc[0].to_dict()
	return {
		"total_vendido": _to_float(row.get("total_vendido")),
		"total_comandas": _to_int(row.get("total_comandas")),
		"items_vendidos": _to_float(row.get("items_vendidos")),
		"ticket_promedio": _to_float(row.get("ticket_promedio")),
	}


def get_ventas_por_hora(conn: Any, view_name: str, filters: Filters, mode: str):
	"""Ventas por hora (para gráfico)."""

	where_sql, params = build_where(filters, mode)
	sql = q_ventas_por_hora(view_name, where_sql)
	return _run_df(conn, sql, params, context="Error ejecutando ventas por hora")


def get_ventas_por_categoria(conn: Any, view_name: str, filters: Filters, mode: str):
	"""Ventas por categoría (para gráfico)."""

	where_sql, params = build_where(filters, mode)
	sql = q_por_categoria(view_name, where_sql)
	return _run_df(conn, sql, params, context="Error ejecutando ventas por categoría")


def get_top_productos(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	limit: int = 20,
):
	"""Top productos por total vendido (para gráfico)."""

	where_sql, params = build_where(filters, mode)
	sql = q_top_productos(view_name, where_sql, limit=limit)
	return _run_df(conn, sql, params, context="Error ejecutando top productos")


def get_detalle(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 500,
):
	"""Tabla detalle (para inspección / validación)."""

	where_sql, params = build_where(filters, mode)
	sql = q_detalle(view_name, where_sql, limit=limit)
	return _run_df(conn, sql, params, context="Error ejecutando detalle")
