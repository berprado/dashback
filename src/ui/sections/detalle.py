from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from src.metrics import get_detalle
from src.ui.formatting import format_detalle_df


@st.fragment
def render_detalle_section(
    *,
    conn: Any,
    startup: Any,
    filters: Any,
    mode_for_metrics: str,
    debug_fn: Callable[[Exception], None],
) -> None:
    st.subheader(":material/receipt_long: Detalle")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver el detalle.")
        return

    with st.expander("Ver detalle (últimas 500 filas)", expanded=False):
        st.caption(
            "Muestra filas del contexto actual sin filtrar por tipo/estado (incluye ventas/cortesías y pendientes/anuladas)."
        )
        cargar_detalle = st.checkbox(
            "Cargar detalle",
            value=False,
            key="detalle_load",
            help=(
                "Ejecuta la consulta de detalle (hasta 500 filas, ordenadas por fecha_emision DESC). "
                "Nota: en la tabla, montos pueden mostrarse como texto formateado (orden puede ser lexicográfico)."
            ),
        )
        try:
            if cargar_detalle:
                detalle = get_detalle(conn, startup.view_name, filters, mode_for_metrics, limit=500)
                if detalle is None or detalle.empty:
                    st.info("Sin datos para el rango seleccionado.")
                else:
                    st.dataframe(format_detalle_df(detalle), width="stretch")
        except Exception as exc:
            st.error(f"Error cargando detalle: {exc}")
            debug_fn(exc)
