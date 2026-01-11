from __future__ import annotations

from typing import Any

from src.query_store import (
	Filters,
	build_where,
	fetch_dataframe,
	q_comandas_emision_times,
	q_impresion_snapshot,
	q_ids_comandas_anuladas,
	q_ids_comandas_impresion_pendiente,
	q_ids_comandas_no_impresas,
	q_ids_comandas_pendientes,
	q_ids_comandas_sin_estado_impresion,
	q_detalle,
	q_estado_operativo,
	q_kpis,
	q_por_usuario,
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

	where_sql, params = build_where(filters, mode, table_alias="v")
	sql = q_kpis(view_name, where_sql)
	df = _run_df(conn, sql, params, context="Error ejecutando KPIs")

	if df is None or df.empty:
		return {
			"total_vendido": 0.0,
			"total_comandas": 0,
			"items_vendidos": 0.0,
			"ticket_promedio": 0.0,
			"total_vendido_impreso_log": 0.0,
			"total_comandas_impreso_log": 0,
			"items_vendidos_impreso_log": 0.0,
			"ticket_promedio_impreso_log": 0.0,
			"total_cortesia": 0.0,
			"items_cortesia": 0.0,
			"comandas_cortesia": 0,
		}

	row = df.iloc[0].to_dict()
	return {
		"total_vendido": _to_float(row.get("total_vendido")),
		"total_comandas": _to_int(row.get("total_comandas")),
		"items_vendidos": _to_float(row.get("items_vendidos")),
		"ticket_promedio": _to_float(row.get("ticket_promedio")),
		"total_vendido_impreso_log": _to_float(row.get("total_vendido_impreso_log")),
		"total_comandas_impreso_log": _to_int(row.get("total_comandas_impreso_log")),
		"items_vendidos_impreso_log": _to_float(row.get("items_vendidos_impreso_log")),
		"ticket_promedio_impreso_log": _to_float(row.get("ticket_promedio_impreso_log")),
		"total_cortesia": _to_float(row.get("total_cortesia")),
		"items_cortesia": _to_float(row.get("items_cortesia")),
		"comandas_cortesia": _to_int(row.get("comandas_cortesia")),
	}


def get_estado_operativo(conn: Any, view_name: str, filters: Filters, mode: str) -> dict[str, Any]:
	"""KPIs operativos (pendientes / impresión).

	Se apoya en los campos humanizados de la vista: `estado_comanda` y `estado_impresion`.
	"""

	where_sql, params = build_where(filters, mode)
	sql = q_estado_operativo(view_name, where_sql)
	df = _run_df(conn, sql, params, context="Error ejecutando estado operativo")

	if df is None or df.empty:
		return {
			"comandas_pendientes": 0,
			"comandas_anuladas": 0,
			"comandas_impresion_pendiente": 0,
			"comandas_sin_estado_impresion": 0,
		}

	row = df.iloc[0].to_dict()
	return {
		"comandas_pendientes": _to_int(row.get("comandas_pendientes")),
		"comandas_anuladas": _to_int(row.get("comandas_anuladas")),
		"comandas_impresion_pendiente": _to_int(row.get("comandas_impresion_pendiente")),
		"comandas_sin_estado_impresion": _to_int(row.get("comandas_sin_estado_impresion")),
	}


def get_ids_comandas_pendientes(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 50,
) -> list[int]:
	"""IDs de comandas pendientes (top por id desc)."""

	where_sql, params = build_where(filters, mode)
	sql = q_ids_comandas_pendientes(view_name, where_sql, limit=limit)
	df = _run_df(conn, sql, params, context="Error obteniendo IDs de comandas pendientes")

	if df is None or df.empty or "id_comanda" not in df.columns:
		return []

	ids: list[int] = []
	for value in df["id_comanda"].tolist():
		iv = _to_int(value)
		if iv:
			ids.append(iv)
	return ids


def get_ids_comandas_no_impresas(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 50,
) -> list[int]:
	"""IDs de comandas no impresas (top por id desc)."""

	where_sql, params = build_where(filters, mode)
	sql = q_ids_comandas_no_impresas(view_name, where_sql, limit=limit)
	df = _run_df(conn, sql, params, context="Error obteniendo IDs de comandas no impresas")

	if df is None or df.empty or "id_comanda" not in df.columns:
		return []

	ids: list[int] = []
	for value in df["id_comanda"].tolist():
		iv = _to_int(value)
		if iv:
			ids.append(iv)
	return ids


def get_ids_comandas_impresion_pendiente(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 50,
) -> list[int]:
	"""IDs de comandas con impresión pendiente (estado_impresion='PENDIENTE')."""

	where_sql, params = build_where(filters, mode)
	sql = q_ids_comandas_impresion_pendiente(view_name, where_sql, limit=limit)
	df = _run_df(conn, sql, params, context="Error obteniendo IDs con impresión pendiente")

	if df is None or df.empty or "id_comanda" not in df.columns:
		return []

	ids: list[int] = []
	for value in df["id_comanda"].tolist():
		iv = _to_int(value)
		if iv:
			ids.append(iv)
	return ids


def get_ids_comandas_sin_estado_impresion(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 50,
) -> list[int]:
	"""IDs de comandas sin estado de impresión (estado_impresion IS NULL)."""

	where_sql, params = build_where(filters, mode)
	sql = q_ids_comandas_sin_estado_impresion(view_name, where_sql, limit=limit)
	df = _run_df(conn, sql, params, context="Error obteniendo IDs sin estado de impresión")

	if df is None or df.empty or "id_comanda" not in df.columns:
		return []

	ids: list[int] = []
	for value in df["id_comanda"].tolist():
		iv = _to_int(value)
		if iv:
			ids.append(iv)
	return ids


def get_ids_comandas_anuladas(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 50,
) -> list[int]:
	"""IDs de comandas anuladas (top por id desc)."""

	where_sql, params = build_where(filters, mode)
	sql = q_ids_comandas_anuladas(view_name, where_sql, limit=limit)
	df = _run_df(conn, sql, params, context="Error obteniendo IDs de comandas anuladas")

	if df is None or df.empty or "id_comanda" not in df.columns:
		return []

	ids: list[int] = []
	for value in df["id_comanda"].tolist():
		iv = _to_int(value)
		if iv:
			ids.append(iv)
	return ids


def get_ventas_por_hora(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	use_impresion_log: bool = False,
):
	"""Ventas por hora (para gráfico)."""

	where_sql, params = build_where(filters, mode, table_alias="v")
	sql = q_ventas_por_hora(view_name, where_sql, use_impresion_log=use_impresion_log)
	return _run_df(conn, sql, params, context="Error ejecutando ventas por hora")


def get_ventas_por_categoria(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	use_impresion_log: bool = False,
):
	"""Ventas por categoría (para gráfico)."""

	where_sql, params = build_where(filters, mode, table_alias="v")
	sql = q_por_categoria(view_name, where_sql, use_impresion_log=use_impresion_log)
	return _run_df(conn, sql, params, context="Error ejecutando ventas por categoría")


def get_ventas_por_usuario(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	limit: int = 20,
	use_impresion_log: bool = False,
):
	"""Ventas por usuario (ranking)."""

	where_sql, params = build_where(filters, mode, table_alias="v")
	sql = q_por_usuario(view_name, where_sql, limit=limit, use_impresion_log=use_impresion_log)
	return _run_df(conn, sql, params, context="Error ejecutando ventas por usuario")


def get_top_productos(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	limit: int = 20,
	*,
	use_impresion_log: bool = False,
):
	"""Top productos por total vendido (para gráfico)."""

	where_sql, params = build_where(filters, mode, table_alias="v")
	sql = q_top_productos(view_name, where_sql, limit=limit, use_impresion_log=use_impresion_log)
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


def get_impresion_snapshot(conn: Any, view_name: str, ids: list[int]):
	"""Devuelve un snapshot de estados de impresión para depuración."""
	sql = q_impresion_snapshot(view_name, ids)
	return _run_df(conn, sql, {}, context="Error ejecutando snapshot de impresión")


def _median_minutes_between(series) -> tuple[float | None, int]:
	"""Devuelve (mediana_en_minutos, cantidad_de_intervalos)."""
	if series is None:
		return None, 0
	try:
		import pandas as pd
	except Exception:
		return None, 0

	dt = pd.to_datetime(series, errors="coerce")
	dt = dt.dropna()
	if len(dt) < 2:
		return None, 0

	deltas = dt.diff().dropna()
	if deltas.empty:
		return None, 0

	minutes = deltas.dt.total_seconds() / 60.0
	minutes = minutes[minutes >= 0]
	if minutes.empty:
		return None, 0

	try:
		median_val = float(minutes.median())
	except Exception:
		median_val = None

	return median_val, int(minutes.shape[0])


def get_actividad_emision_comandas(
	conn: Any,
	view_name: str,
	filters: Filters,
	mode: str,
	*,
	recent_n: int = 10,
) -> dict[str, Any]:
	"""Métricas de actividad basadas en `fecha_emision`.

	Calcula:
	- Hora/fecha de última comanda (MAX fecha_emision)
	- Minutos desde la última comanda (vs reloj del servidor Streamlit)
	- Mediana de minutos entre comandas (últimas N)
	- Mediana de minutos entre comandas (todo el rango/operativa)

	Nota: Se calcula por comanda (id_comanda), no por ítem.
	"""

	where_sql, params = build_where(filters, mode)

	# Últimas N comandas (ordenadas asc para poder hacer diff).
	recent_df = _run_df(
		conn,
		q_comandas_emision_times(view_name, where_sql, limit=int(recent_n)),
		params,
		context="Error obteniendo timestamps de emisión (últimas comandas)",
	)

	# Todas las comandas del contexto (para ritmo global).
	all_df = _run_df(
		conn,
		q_comandas_emision_times(view_name, where_sql, limit=None),
		params,
		context="Error obteniendo timestamps de emisión (todas las comandas)",
	)

	last_ts = None
	minutes_since_last = None

	try:
		import pandas as pd
		if recent_df is not None and not recent_df.empty and "fecha_emision" in recent_df.columns:
			last_ts = pd.to_datetime(recent_df["fecha_emision"].max(), errors="coerce")
			if pd.notna(last_ts):
				now = pd.Timestamp.now()
				delta = now - last_ts
				minutes_since_last = float(delta.total_seconds() / 60.0)
			else:
				last_ts = None
				minutes_since_last = None
	except Exception:
		last_ts = None
		minutes_since_last = None

	recent_median_min, recent_intervals = _median_minutes_between(
		recent_df["fecha_emision"] if recent_df is not None and "fecha_emision" in getattr(recent_df, "columns", []) else None
	)
	all_median_min, all_intervals = _median_minutes_between(
		all_df["fecha_emision"] if all_df is not None and "fecha_emision" in getattr(all_df, "columns", []) else None
	)

	return {
		"last_ts": last_ts,
		"minutes_since_last": minutes_since_last,
		"recent_median_min": recent_median_min,
		"recent_intervals": recent_intervals,
		"all_median_min": all_median_min,
		"all_intervals": all_intervals,
		"recent_n": int(recent_n),
	}
