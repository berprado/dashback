from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics import (
    get_cogs_por_comanda,
    get_consumo_sin_valorar,
    get_consumo_valorizado,
    get_pour_cost_por_combo,
    get_wac_cogs_detalle,
    get_wac_cogs_summary,
)
from src.ui.comanda_details import render_comanda_expanders_from_df
from src.ui.formatting import (
    apply_plotly_bs,
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

    using_fallback = False
    try:
        wac_cogs = get_wac_cogs_summary(conn, "vw_margen_comanda", filters, mode_for_metrics)
        st.session_state["margenes_fallback"] = dict(wac_cogs)

        st.markdown('<div class="metric-scope metric-kpis">', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)

        total_ventas = float(wac_cogs.get("total_ventas") or 0)
        total_cogs = float(wac_cogs.get("total_cogs") or 0)
        total_margen = float(wac_cogs.get("total_margen") or 0)
        margen_pct = float(wac_cogs.get("margen_pct") or 0)
        pour_cost_pct = float(wac_cogs.get("pour_cost_pct") or 0)

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
        with m5:
            # Umbrales solicitados: <28 (verde), 28-30 (amarillo), >30 (rojo)
            pc_info = "**Pour Cost %**\n\n" f"# {pour_cost_pct:.2f} %"
            
            if pour_cost_pct < 28:
                st.success(pc_info, icon=":material/check_circle:")
            elif pour_cost_pct <= 30:
                st.warning(pc_info, icon=":material/warning:")
            else:
                st.error(pc_info, icon=":material/error:")


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

        with st.expander("Pour Cost por ítems (combos + comandables, umbral 30%)", expanded=False):
            st.caption(
                "Clasifica ítems (combos y comandables) según su pour cost: por debajo o igual a 30% y por encima de 30%. "
                "El COGS por ítem se estima por prorrateo del COGS de comanda según participación en ventas."
            )
            cargar_pour_combo = st.checkbox(
                "Cargar pour cost por ítems",
                value=False,
                key="pour_cost_combo_load",
                help=(
                    "Trae ranking de ítems (combos + comandables) con ventas, COGS asignado y pour cost %. "
                    "Permite priorizar ítems con pour cost por encima de 30%."
                ),
            )
            limit_pour_combo = st.number_input(
                "Límite ítems",
                min_value=10,
                max_value=300,
                value=60,
                step=10,
                key="limit_pour_cost_combo",
                help="Máximo de ítems a analizar en el gráfico y tabla.",
            )

            if cargar_pour_combo:
                pour_combo_df = get_pour_cost_por_combo(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit_pour_combo),
                )

                if pour_combo_df is None or pour_combo_df.empty:
                    st.info("Sin datos de ítems para el contexto seleccionado.")
                else:
                    data = pour_combo_df.copy()
                    data["pour_cost_pct"] = pd.to_numeric(data["pour_cost_pct"], errors="coerce").fillna(0.0)
                    data["cantidad_vendida"] = pd.to_numeric(data["cantidad_vendida"], errors="coerce").fillna(0.0)
                    data["cogs_combo"] = pd.to_numeric(data["cogs_combo"], errors="coerce").fillna(0.0)
                    data["ventas_combo"] = pd.to_numeric(data["ventas_combo"], errors="coerce").fillna(0.0)
                    data["cogs_asignado"] = pd.to_numeric(data["cogs_asignado"], errors="coerce").fillna(0.0)
                    data["tipo_item"] = data["tipo_item"].fillna("Item")
                    data["estado_umbral"] = data["pour_cost_pct"].apply(
                        lambda x: "Sobre 30%" if float(x) > 30 else "≤ 30%"
                    )

                    sobre_30 = int((data["pour_cost_pct"] > 30).sum())
                    bajo_igual_30 = int((data["pour_cost_pct"] <= 30).sum())
                    c1, c2 = st.columns(2)
                    c1.metric("Ítems > 30%", sobre_30, border=True)
                    c2.metric("Ítems ≤ 30%", bajo_igual_30, border=True)

                    chart_df = data.sort_values("pour_cost_pct", ascending=False)
                    fig = px.bar(
                        chart_df,
                        x="pour_cost_pct",
                        y="nombre_combo",
                        color="estado_umbral",
                        orientation="h",
                        title="Pour Cost % por ítem",
                        labels={
                            "pour_cost_pct": "Pour Cost %",
                            "nombre_combo": "Ítem",
                            "estado_umbral": "Clasificación",
                        },
                        color_discrete_map={"Sobre 30%": "#ef4444", "≤ 30%": "#22c55e"},
                        hover_data={
                            "tipo_item": True,
                            "cantidad_vendida": ":,.2f",
                            "cogs_combo": ":,.4f",
                            "ventas_combo": ":,.2f",
                            "cogs_asignado": ":,.2f",
                        },
                    )
                    fig.add_vline(x=30, line_dash="dash", line_color="#f59e0b")
                    fig.update_layout(
                        height=max(420, int(len(chart_df) * 34)),
                        margin=dict(l=220, r=10, t=40, b=10),
                    )
                    fig.update_yaxes(
                        automargin=True,
                        categoryorder="array",
                        categoryarray=chart_df["nombre_combo"].tolist()[::-1],
                    )
                    apply_plotly_bs(fig, axis="x", decimals=2)
                    st.plotly_chart(fig, width="stretch")

                    table_df = chart_df.copy()
                    table_df["cogs_combo"] = table_df["cogs_combo"].apply(lambda x: format_bs(x, decimals=4))
                    table_df["cantidad_vendida"] = table_df["cantidad_vendida"].apply(
                        lambda x: f"{float(x):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
                    )
                    table_df["ventas_combo"] = table_df["ventas_combo"].apply(format_bs)
                    table_df["cogs_asignado"] = table_df["cogs_asignado"].apply(format_bs)
                    table_df["pour_cost_pct"] = table_df["pour_cost_pct"].apply(lambda x: f"{float(x):.2f} %")
                    st.dataframe(
                        table_df[
                            [
                                "tipo_item",
                                "nombre_combo",
                                "cogs_combo",
                                "cantidad_vendida",
                                "ventas_combo",
                                "cogs_asignado",
                                "pour_cost_pct",
                                "estado_umbral",
                            ]
                        ],
                        width="stretch",
                    )
    except Exception as exc:
        st.warning("No se pudo calcular P&L. Mostrando datos en cache.")
        wac_cogs = st.session_state.get("margenes_fallback")
        if not wac_cogs:
            st.error(f"Error calculando P&L: {exc}")
            debug_fn(exc)
            return
        using_fallback = True
        debug_fn(exc)

    if using_fallback:
        st.caption("Mostrando datos en cache (último cálculo exitoso).")
