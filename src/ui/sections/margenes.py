from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from src.metrics import (
    get_cogs_por_comanda,
    get_consumo_sin_valorar,
    get_consumo_valorizado,
    get_wac_cogs_detalle,
    get_wac_cogs_summary,
)
from src.ui.comanda_details import render_comanda_expanders_from_df
from src.ui.formatting import (
    format_bs,
    format_cogs_comanda_df,
    format_consumo_sin_valorar_df,
    format_consumo_valorizado_df,
    format_margen_comanda_df,
)


@st.fragment
def render_margenes_section(
    *,
    conn: Any,
    startup: Any,
    filters: Any,
    mode_for_metrics: str,
    debug_fn: Callable[[Exception], None],
) -> None:
    st.subheader(":material/payments: Márgenes & Rentabilidad")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver márgenes.")
        return

    try:
        wac_cogs = get_wac_cogs_summary(conn, "vw_margen_comanda", filters, mode_for_metrics)

        st.markdown('<div class="metric-scope metric-kpis">', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)

        total_ventas = float(wac_cogs.get("total_ventas") or 0)
        total_cogs = float(wac_cogs.get("total_cogs") or 0)
        total_margen = float(wac_cogs.get("total_margen") or 0)
        margen_pct = float(wac_cogs.get("margen_pct") or 0)

        m1.metric(
            "Ventas brutas",
            format_bs(total_ventas),
            help=(
                "Suma total facturado en el contexto actual (comandas VENTA finalizadas). "
                "Base para cálculo de margen = ventas - cogs."
            ),
            border=True,
        )
        m2.metric(
            "COGS",
            format_bs(total_cogs),
            help=(
                "Costo de los insumos consumidos (combos + comandables integrados). "
                "Utilizado para calcular la utilidad bruta."
            ),
            border=True,
        )
        m3.metric(
            "Margen bruto",
            format_bs(total_margen),
            help=(
                "Utilidad bruta = ventas - cogs. "
                "Indicador clave para control de rentabilidad operativa."
            ),
            border=True,
        )
        m4.metric(
            "Margen %",
            f"{margen_pct:.2f} %",
            help=(
                "Porcentaje de margen bruto = (margen / ventas) × 100. "
                "Métrica ejecutiva: validación contra ope_conciliacion."
            ),
            border=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Detalle P&L por comanda", expanded=False):
            st.caption(
                "Una fila por comanda con ventas, COGS y margen. "
                "Útil para auditoría fina (márgenes anómalos / receta / WAC)."
            )
            cargar_detalle_pnl = st.checkbox(
                "Cargar detalle P&L",
                value=False,
                key="pnl_detalle_load",
                help=(
                    "Ejecuta la consulta sobre vw_margen_comanda para el contexto actual. "
                    "Los montos se formatean como texto (orden lexicográfico)."
                ),
            )
            limit_pnl = st.number_input(
                "Límite",
                min_value=50,
                max_value=2000,
                value=300,
                step=50,
                help="Máximo de filas a traer, ordenadas por id_comanda DESC.",
            )

            if cargar_detalle_pnl:
                detalle_pnl = get_wac_cogs_detalle(
                    conn,
                    "vw_margen_comanda",
                    filters,
                    mode_for_metrics,
                    limit=int(limit_pnl),
                )
                if detalle_pnl is None or detalle_pnl.empty:
                    st.info("Sin datos para el contexto seleccionado.")
                else:
                    st.dataframe(format_margen_comanda_df(detalle_pnl), width="stretch")

                    st.subheader("Detalles de Comandas")
                    render_comanda_expanders_from_df(conn, detalle_pnl, startup.view_name, mode_for_metrics)

        with st.expander("Consumo valorizado de insumos", expanded=False):
            st.caption(
                "Insumos consumidos por producto con cantidad, WAC y costo. "
                "Consulta logística: conciliación de inventario, detección de mermas y análisis de costos."
            )
            cargar_consumo = st.checkbox(
                "Cargar consumo valorizado",
                value=False,
                key="consumo_valorizado_load",
                help=(
                    "Ejecuta la consulta sobre vw_consumo_valorizado_operativa para el contexto actual. "
                    "Ordenado por costo_consumo DESC."
                ),
            )
            limit_consumo = st.number_input(
                "Límite consumo",
                min_value=50,
                max_value=2000,
                value=300,
                step=50,
                key="limit_consumo_valorizado",
                help="Máximo de productos a traer, ordenados por costo_consumo DESC.",
            )

            if cargar_consumo:
                consumo_val = get_consumo_valorizado(
                    conn,
                    "vw_consumo_valorizado_operativa",
                    filters,
                    mode_for_metrics,
                    limit=int(limit_consumo),
                )
                if consumo_val is None or consumo_val.empty:
                    st.info("Sin datos para el contexto seleccionado.")
                else:
                    st.dataframe(format_consumo_valorizado_df(consumo_val), width="stretch")

        with st.expander("Consumo sin valorar (sanidad de cantidades)", expanded=False):
            st.caption(
                "Solo cantidades consumidas, sin WAC ni costos. "
                "Sanidad: si algo está mal aquí, no es WAC/margen sino receta/multiplicación/unidades. "
                "Regla: si el consumo está mal, todo lo demás estará mal aunque el WAC sea perfecto."
            )
            cargar_sin_valorar = st.checkbox(
                "Cargar consumo sin valorar",
                value=False,
                key="consumo_sin_valorar_load",
                help=(
                    "Ejecuta la consulta sobre vw_consumo_insumos_operativa para el contexto actual. "
                    "Ordenado por cantidad_consumida_base DESC."
                ),
            )
            limit_sin_valorar = st.number_input(
                "Límite sin valorar",
                min_value=50,
                max_value=2000,
                value=300,
                step=50,
                key="limit_consumo_sin_valorar",
                help="Máximo de productos a traer, ordenados por cantidad_consumida_base DESC.",
            )

            if cargar_sin_valorar:
                consumo_sin_val = get_consumo_sin_valorar(
                    conn,
                    "vw_consumo_insumos_operativa",
                    filters,
                    mode_for_metrics,
                    limit=int(limit_sin_valorar),
                )
                if consumo_sin_val is None or consumo_sin_val.empty:
                    st.info("Sin datos para el contexto seleccionado.")
                else:
                    st.dataframe(format_consumo_sin_valorar_df(consumo_sin_val), width="stretch")

        with st.expander("COGS por comanda (sin ventas)", expanded=False):
            st.caption(
                "Costo puro por comanda, sin precio de venta. "
                "Ideal para cortesías (tienen COGS pero no ventas) y auditoría de consumo. "
                "Bisagra entre inventario y finanzas."
            )
            cargar_cogs = st.checkbox(
                "Cargar COGS por comanda",
                value=False,
                key="cogs_comanda_load",
                help=(
                    "Ejecuta la consulta sobre vw_cogs_comanda para el contexto actual. "
                    "Ordenado por cogs_comanda DESC."
                ),
            )
            limit_cogs = st.number_input(
                "Límite COGS",
                min_value=50,
                max_value=2000,
                value=300,
                step=50,
                key="limit_cogs_comanda",
                help="Máximo de comandas a traer, ordenadas por cogs_comanda DESC.",
            )

            if cargar_cogs:
                cogs_df = get_cogs_por_comanda(
                    conn,
                    "vw_cogs_comanda",
                    filters,
                    mode_for_metrics,
                    limit=int(limit_cogs),
                )
                if cogs_df is None or cogs_df.empty:
                    st.info("Sin datos para el contexto seleccionado.")
                else:
                    st.dataframe(format_cogs_comanda_df(cogs_df), width="stretch")

                    st.subheader("Detalles de Comandas")
                    render_comanda_expanders_from_df(conn, cogs_df, startup.view_name, mode_for_metrics)
    except Exception as exc:
        st.error(f"Error calculando P&L: {exc}")
        debug_fn(exc)
