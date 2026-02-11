from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from src.metrics import (
    get_estado_operativo,
    get_ids_comandas_anuladas,
    get_ids_comandas_impresion_pendiente,
    get_ids_comandas_pendientes,
    get_ids_comandas_sin_estado_impresion,
    get_impresion_snapshot,
)
from src.ui.formatting import format_int


def render_estado_operativo_section(
    *,
    conn: Any,
    startup: Any,
    filters: Any,
    mode_for_metrics: str,
    debug_fn: Callable[[Exception], None],
) -> None:
    st.subheader("Estado operativo")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver estado operativo.")
        return

    try:
        estado = get_estado_operativo(conn, startup.view_name, filters, mode_for_metrics)
        st.markdown('<div class="metric-scope metric-estado-operativo">', unsafe_allow_html=True)
        e1, e2, e3, e4 = st.columns(4)
        e1.metric(
            "Comandas pendientes",
            format_int(estado["comandas_pendientes"]),
            help="Comandas con estado_comanda='PENDIENTE' (cualquier tipo_salida/estado_impresion).",
            border=True,
        )
        e2.metric(
            "Comandas anuladas",
            format_int(estado.get("comandas_anuladas")),
            help="Comandas con estado_comanda='ANULADO' (cualquier tipo_salida/estado_impresion).",
            border=True,
        )
        e3.metric(
            "Impresión pendiente",
            format_int(estado["comandas_impresion_pendiente"]),
            help="Comandas no anuladas con estado_impresion='PENDIENTE' (en cola/por procesar).",
            border=True,
        )
        e4.metric(
            "Sin estado impresión",
            format_int(estado["comandas_sin_estado_impresion"]),
            help=(
                "Comandas no anuladas con estado_impresion IS NULL. "
                "Puede indicar que aún no fue procesada/impresa o que el POS no registró el estado."
            ),
            border=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander(
            "Ver IDs de comandas (pendientes / impresión pendiente / sin estado / anuladas)",
            expanded=False,
        ):
            cargar_ids = st.checkbox(
                "Cargar IDs",
                value=False,
                key="estado_operativo_load_ids",
                help=(
                    "Carga los IDs desde la base de datos para el contexto actual. "
                    "Pendientes: estado_comanda='PENDIENTE'. "
                    "Anuladas: estado_comanda='ANULADO'. "
                    "Impresión pendiente: no anuladas con estado_impresion='PENDIENTE'. "
                    "Sin estado: no anuladas con estado_impresion IS NULL."
                ),
            )
            limit = st.number_input(
                "Límite",
                min_value=10,
                max_value=200,
                value=50,
                step=10,
                help=(
                    "Máximo de IDs a traer por categoría. "
                    "Se ordena por id_comanda DESC y se aplica LIMIT."
                ),
            )

            if cargar_ids:
                ids_pend = get_ids_comandas_pendientes(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )
                ids_imp_pend = get_ids_comandas_impresion_pendiente(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )
                ids_sin_ei = get_ids_comandas_sin_estado_impresion(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )
                ids_anul = get_ids_comandas_anuladas(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )

                i1, i2, i3, i4 = st.columns(4)
                i1.caption("Pendientes")
                i1.caption(f"Mostrando {len(ids_pend)} (límite {int(limit)})")
                i1.code(", ".join(map(str, ids_pend)) if ids_pend else "—")
                i2.caption("Impresión pendiente")
                i2.caption(f"Mostrando {len(ids_imp_pend)} (límite {int(limit)})")
                i2.code(", ".join(map(str, ids_imp_pend)) if ids_imp_pend else "—")
                i3.caption("Sin estado impresión")
                i3.caption(f"Mostrando {len(ids_sin_ei)} (límite {int(limit)})")
                i3.code(", ".join(map(str, ids_sin_ei)) if ids_sin_ei else "—")
                i4.caption("Anuladas")
                i4.caption(f"Mostrando {len(ids_anul)} (límite {int(limit)})")
                i4.code(", ".join(map(str, ids_anul)) if ids_anul else "—")

                st.divider()
                diagnosticar = st.checkbox(
                    "Diagnosticar estado de impresión de estos IDs",
                    value=False,
                    key="estado_operativo_diag_impresion",
                    help=(
                        "Cruza lo que devuelve la vista del dashboard (estado_impresion) con "
                        "bar_comanda.estado_impresion y el último log (vw_comanda_ultima_impresion). "
                        "Útil para entender por qué una comanda aparece como PENDIENTE/NULL en la vista."
                    ),
                )
                if diagnosticar:
                    ids_all = sorted(set(ids_pend + ids_imp_pend + ids_sin_ei + ids_anul))
                    snap = get_impresion_snapshot(conn, startup.view_name, ids_all, mode=mode_for_metrics)
                    st.dataframe(snap, width="stretch")
    except Exception as exc:
        st.error(f"Error cargando estado operativo: {exc}")
        debug_fn(exc)
