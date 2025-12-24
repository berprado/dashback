from __future__ import annotations

from typing import Any

from src.query_store import Filters, build_where, fetch_dataframe, q_kpis, q_ventas_por_hora


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
	df = fetch_dataframe(conn, q_kpis(view_name, where_sql), params)

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
	return fetch_dataframe(conn, q_ventas_por_hora(view_name, where_sql), params)
