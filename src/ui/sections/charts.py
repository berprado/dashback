from __future__ import annotations

from functools import partial
from typing import Any, Callable

import streamlit as st

from src.metrics import (
    get_top_productos,
    get_ventas_por_categoria,
    get_ventas_por_hora,
    get_ventas_por_usuario,
)
from src.ui.components import bar_chart, line_chart, pie_chart, render_chart_section
from src.ui.layout import render_filter_context_badge


@st.fragment
def render_charts_section(
    *,
    conn: Any,
    startup: Any,
    filters: Any,
    mode_for_metrics: str,
    ventas_use_impresion_log: bool,
    grafico_categoria: str,
    limit_top_productos: int,
    limit_top_usuarios: int,
    mostrar_promedio_hora: bool,
    debug_fn: Callable[[Exception], None],
) -> None:
    render_filter_context_badge(filters, mode_for_metrics, ventas_use_impresion_log)

    g1, g2 = st.columns(2)

    with g1:
        render_chart_section(
            title="Ventas por hora",
            caption=(
                "Ventas finalizadas agrupadas por HOUR(fecha_emision) en el contexto actual "
                + ("(con log de impresión)." if ventas_use_impresion_log else "(estricto por vista).")
            ),
            data_fn=partial(
                get_ventas_por_hora,
                conn,
                startup.view_name if startup else "",
                filters,
                mode_for_metrics,
                use_impresion_log=ventas_use_impresion_log,
            ),
            chart_fn=lambda df: line_chart(
                df,
                x="hora",
                y="total_vendido",
                title=None,
                money=True,
                hover_data={"comandas": True, "items": True},
                markers=True,
                show_average=mostrar_promedio_hora,
            ),
            conn=conn,
            startup=startup,
            debug_fn=debug_fn,
            check_realtime_empty=True,
        )

    with g2:
        render_chart_section(
            title="Ventas por categoría",
            caption=(
                "Ventas finalizadas agrupadas por categoría en el contexto actual "
                + ("(con log de impresión)." if ventas_use_impresion_log else "(estricto por vista).")
            ),
            data_fn=partial(
                get_ventas_por_categoria,
                conn,
                startup.view_name if startup else "",
                filters,
                mode_for_metrics,
                use_impresion_log=ventas_use_impresion_log,
            ),
            chart_fn=(
                lambda df: bar_chart(
                    df,
                    x="categoria",
                    y="total_vendido",
                    title=None,
                    money=True,
                    hover_data={"unidades": True, "comandas": True},
                )
                if grafico_categoria == "Barras"
                else pie_chart(
                    df,
                    names="categoria",
                    values="total_vendido",
                    title=None,
                    money=True,
                    hover_data=["unidades", "comandas"],
                )
            ),
            conn=conn,
            startup=startup,
            debug_fn=debug_fn,
        )

    g3, g4 = st.columns(2)

    with g3:
        render_chart_section(
            title="Top productos",
            caption=(
                "Ranking por total vendido de ventas finalizadas en el contexto actual "
                + ("(con log de impresión)." if ventas_use_impresion_log else "(estricto por vista).")
            ),
            data_fn=partial(
                get_top_productos,
                conn,
                startup.view_name if startup else "",
                filters,
                mode_for_metrics,
                limit=int(limit_top_productos),
                use_impresion_log=ventas_use_impresion_log,
            ),
            chart_fn=lambda df: bar_chart(
                df,
                x="total_vendido",
                y="nombre",
                title=None,
                orientation="h",
                money=True,
                hover_data={"categoria": True, "unidades": True},
            ),
            conn=conn,
            startup=startup,
            debug_fn=debug_fn,
        )

    with g4:
        render_chart_section(
            title="Ventas por usuario",
            caption=(
                "Ranking por total vendido de ventas finalizadas en el contexto actual "
                + ("(con log de impresión)." if ventas_use_impresion_log else "(estricto por vista).")
            ),
            data_fn=partial(
                get_ventas_por_usuario,
                conn,
                startup.view_name if startup else "",
                filters,
                mode_for_metrics,
                limit=int(limit_top_usuarios),
                use_impresion_log=ventas_use_impresion_log,
            ),
            chart_fn=lambda df: bar_chart(
                df,
                x="total_vendido",
                y="usuario_reg",
                title=None,
                orientation="h",
                money=True,
                hover_data={"comandas": True, "items": True, "ticket_promedio": ":.2f"},
            ),
            conn=conn,
            startup=startup,
            debug_fn=debug_fn,
        )
