from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from src.metrics import get_actividad_emision_comandas, get_kpis
from src.ui.formatting import format_bs, format_int


@st.fragment
def render_kpis_section(
    *,
    conn: Any,
    startup: Any,
    filters: Any,
    mode_for_metrics: str,
    ventas_use_impresion_log: bool,
    debug_fn: Callable[[Exception], None],
) -> None:
    st.subheader(":material/monitoring: KPIs")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver KPIs.")
        return

    using_fallback = False
    try:
        kpis = get_kpis(conn, startup.view_name, filters, mode_for_metrics)
        st.session_state["kpis_fallback"] = dict(kpis)

        st.markdown('<div class="metric-scope metric-kpis">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)

        total_vendido = (
            float(kpis.get("total_vendido_impreso_log") or 0)
            if ventas_use_impresion_log
            else float(kpis.get("total_vendido") or 0)
        )
        total_comandas = (
            int(kpis.get("total_comandas_impreso_log") or 0)
            if ventas_use_impresion_log
            else int(kpis.get("total_comandas") or 0)
        )
        items_vendidos = (
            float(kpis.get("items_vendidos_impreso_log") or 0)
            if ventas_use_impresion_log
            else float(kpis.get("items_vendidos") or 0)
        )
        ticket_promedio = (
            float(kpis.get("ticket_promedio_impreso_log") or 0)
            if ventas_use_impresion_log
            else float(kpis.get("ticket_promedio") or 0)
        )

        ventas_help = (
            "Ventas finalizadas (tipo_salida='VENTA', estado_comanda='PROCESADO') con señal de IMPRESO: "
            "se acepta IMPRESO si la vista lo marca como IMPRESO o si vw_comanda_ultima_impresion indica IMPRESO."
            if ventas_use_impresion_log
            else (
                "Ventas finalizadas (tipo_salida='VENTA', estado_comanda='PROCESADO', estado_impresion='IMPRESO'): "
                "suma de sub_total en el contexto seleccionado."
            )
        )

        c1.metric(
            "Total vendido",
            format_bs(total_vendido),
            help=ventas_help,
            border=True,
        )
        c2.metric(
            "Comandas",
            format_int(total_comandas),
            help=(
                "Ventas finalizadas (VENTA/PROCESADO) con señal de IMPRESO según el modo actual: "
                "cantidad de comandas distintas (COUNT DISTINCT id_comanda)."
            ),
            border=True,
        )
        c3.metric(
            "Ítems",
            format_int(items_vendidos),
            help=(
                "Ventas finalizadas (VENTA/PROCESADO) con señal de IMPRESO según el modo actual: "
                "suma de cantidades (SUM cantidad)."
            ),
            border=True,
        )
        c4.metric(
            "Ticket promedio",
            format_bs(ticket_promedio),
            help="Ventas finalizadas (según el modo actual): total vendido / comandas (redondeado).",
            border=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Diagnóstico de impresión (impacto en ventas)", expanded=False):
            st.caption(
                "Compara la venta finalizada estricta (estado_impresion='IMPRESO' en la vista) vs una señal "
                "'efectiva' que además toma el último estado del log de impresión (vw_comanda_ultima_impresion)."
            )

            st.markdown(
                '<div class="metric-scope metric-diagnostico-impresion">',
                unsafe_allow_html=True,
            )
            d1, d2, d3 = st.columns(3)

            total_log = float(kpis.get("total_vendido_impreso_log") or 0)
            total_strict = float(kpis.get("total_vendido") or 0)
            delta = total_log - total_strict

            d1.metric(
                "Total vendido (con log)",
                format_bs(total_log),
                help=(
                    "Ventas finalizadas donde se acepta IMPRESO si la vista lo marca como IMPRESO "
                    "o si vw_comanda_ultima_impresion indica IMPRESO para la comanda."
                ),
                border=True,
            )
            d2.metric(
                "Comandas (con log)",
                format_int(kpis.get("total_comandas_impreso_log") or 0),
                help="COUNT DISTINCT id_comanda bajo la misma regla 'con log'.",
                border=True,
            )
            d3.metric(
                "Delta vs estricto",
                format_bs(delta),
                help="Diferencia: total vendido (con log) - total vendido (estricto).",
                border=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        try:
            act = get_actividad_emision_comandas(
                conn,
                startup.view_name,
                filters,
                mode_for_metrics,
                recent_n=10,
            )

            last_ts = act.get("last_ts")
            last_ts_txt = None
            try:
                if last_ts is not None:
                    last_ts_txt = last_ts.strftime("%H:%M:%S")
            except Exception:
                last_ts_txt = None

            minutes_since_last = act.get("minutes_since_last")
            minutes_since_txt = None
            try:
                if minutes_since_last is not None:
                    minutes_since_txt = f"{float(minutes_since_last):.0f}"
            except Exception:
                minutes_since_txt = None

            recent_median = act.get("recent_median_min")
            all_median = act.get("all_median_min")
            recent_n = act.get("recent_n")
            recent_intervals = act.get("recent_intervals")
            all_intervals = act.get("all_intervals")

            st.markdown('<div class="metric-scope metric-kpis">', unsafe_allow_html=True)
            a1, a2, a3, a4 = st.columns(4)
            a1.metric(
                "Última comanda",
                last_ts_txt,
                help=(
                    "Hora (MAX fecha_emision) de la última comanda emitida (por id_comanda) en el contexto actual. "
                    "Incluye ventas/cortesías y no filtra por estado (pendiente/anulada)."
                ),
                border=True,
            )
            a2.metric(
                "Min desde última",
                minutes_since_txt,
                help=(
                    "Minutos transcurridos desde la última fecha_emision (según el reloj del servidor donde corre Streamlit)."
                ),
                border=True,
            )
            a3.metric(
                f"Ritmo (últimas {int(recent_n or 10)})",
                (f"{float(recent_median):.1f} min" if recent_median is not None else None),
                help=(
                    "Mediana de minutos entre comandas consecutivas (por id_comanda), sin filtrar por tipo/estado. "
                    + (f"Intervalos usados: {int(recent_intervals or 0)}.")
                ),
                border=True,
            )
            a4.metric(
                "Ritmo (operativa/rango)",
                (f"{float(all_median):.1f} min" if all_median is not None else None),
                help=(
                    "Mediana de minutos entre comandas consecutivas en todo el contexto actual, sin filtrar por tipo/estado. "
                    + (f"Intervalos usados: {int(all_intervals or 0)}.")
                ),
                border=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as exc:
            st.warning(f"No se pudo calcular actividad: {exc}")
            debug_fn(exc)

        st.markdown('<div class="metric-scope metric-kpis">', unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric(
            "Total cortesías",
            format_bs(kpis["total_cortesia"]),
            help=(
                "Cortesías finalizadas (tipo_salida='CORTESIA', estado_comanda='PROCESADO', estado_impresion='IMPRESO'): "
                "suma de cor_subtotal_anterior (si existe) o sub_total."
            ),
            border=True,
        )
        k2.metric(
            "Comandas cortesía",
            format_int(kpis["comandas_cortesia"]),
            help="Cortesías finalizadas (CORTESIA/PROCESADO/IMPRESO): cantidad de comandas distintas.",
            border=True,
        )
        k3.metric(
            "Ítems cortesía",
            format_int(kpis["items_cortesia"]),
            help="Cortesías finalizadas (CORTESIA/PROCESADO/IMPRESO): suma de cantidad.",
            border=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)
    except Exception as exc:
        st.warning("No se pudieron calcular los KPIs. Mostrando datos en cache.")
        kpis = st.session_state.get("kpis_fallback")
        if not kpis:
            st.error(f"Error calculando KPIs: {exc}")
            debug_fn(exc)
            return
        using_fallback = True
        debug_fn(exc)

    if using_fallback:
        st.caption("Mostrando datos en cache (último cálculo exitoso).")
