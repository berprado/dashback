from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from src.db import get_connection
from src.query_store import (
    Q_STARTUP_ACTIVE_OPERATION,
    Q_STARTUP_HAS_REALTIME_ROWS,
    Q_STARTUP_LAST_CLOSED_OPERATION,
    fetch_dataframe,
)


VIEW_REALTIME = "comandas_v6"
VIEW_HISTORICAL = "comandas_v6_todas"


@dataclass(frozen=True)
class StartupContext:
    """Contexto de arranque del dashboard.

    Nota: La lógica completa (operativa activa vs histórico) se implementará
    según docs/01-flujo_inicio_dashboard.md y docs/02-guia_dashboard_backstage.md.
    """

    mode: Literal["realtime", "historical"]
    view_name: str
    operacion_id: int | None
    estado_operacion_id: int | None
    estado_operacion: str | None
    has_rows: bool
    message: str


def _first_row(df: pd.DataFrame) -> dict[str, Any] | None:
    if df is None or df.empty:
        return None
    return df.iloc[0].to_dict()


def determine_startup_context(conn: Any | None = None) -> StartupContext:
    """Determina el contexto operativo inicial (tiempo real vs histórico).

    Reglas (docs/01-flujo_inicio_dashboard.md):
    - Tiempo real: existe `ope_operacion` HAB con `estado_operacion IN (22,24)` (usar `comandas_v6`).
    - Histórico: no existe activa; por defecto usar la última cerrada (23) y la vista `comandas_v6_todas`.
    """

    if conn is None:
        conn = get_connection()

    active = _first_row(fetch_dataframe(conn, Q_STARTUP_ACTIVE_OPERATION))
    if active is not None:
        has_rows = not fetch_dataframe(conn, Q_STARTUP_HAS_REALTIME_ROWS).empty

        estado_operacion = active.get("estado_operacion")
        estado_operacion_id = active.get("estado_operacion_id")
        operacion_id = active.get("id_operacion")

        message = (
            ":material/check_circle: Operativa activa — esperando primeras comandas."
            if not has_rows
            else f":material/check_circle: Operativa #{operacion_id} — {estado_operacion or 'ACTIVA'}"
        )

        return StartupContext(
            mode="realtime",
            view_name=VIEW_REALTIME,
            operacion_id=int(operacion_id) if operacion_id is not None else None,
            estado_operacion_id=int(estado_operacion_id)
            if estado_operacion_id is not None
            else None,
            estado_operacion=str(estado_operacion) if estado_operacion is not None else None,
            has_rows=has_rows,
            message=message,
        )

    closed = _first_row(fetch_dataframe(conn, Q_STARTUP_LAST_CLOSED_OPERATION))
    operacion_id = closed.get("id_operacion") if closed else None
    estado_operacion_id = closed.get("estado_operacion_id") if closed else None
    estado_operacion = closed.get("estado_operacion") if closed else None

    message = (
        ":material/history: No hay operativa activa — mostrando histórico."
        if operacion_id is not None
        else ":material/history: No hay operativa activa ni operativas cerradas — seleccione un rango para ver histórico."
    )

    return StartupContext(
        mode="historical",
        view_name=VIEW_HISTORICAL,
        operacion_id=int(operacion_id) if operacion_id is not None else None,
        estado_operacion_id=int(estado_operacion_id) if estado_operacion_id is not None else None,
        estado_operacion=str(estado_operacion) if estado_operacion is not None else None,
        has_rows=False,
        message=message,
    )
