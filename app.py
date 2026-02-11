from __future__ import annotations

from functools import partial

import streamlit as st

from src.db import get_connection
from src.metrics import (
    QueryExecutionError,
    get_actividad_emision_comandas,
    get_detalle,
    get_estado_operativo,
    get_ids_comandas_anuladas,
    get_ids_comandas_impresion_pendiente,
    get_ids_comandas_pendientes,
    get_ids_comandas_sin_estado_impresion,
    get_kpis,
    get_impresion_snapshot,
    get_top_productos,
    get_ventas_por_categoria,
    get_ventas_por_hora,
    get_ventas_por_usuario,
    get_wac_cogs_summary,
    get_wac_cogs_detalle,
    get_consumo_valorizado,
    get_consumo_sin_valorar,
    get_cogs_por_comanda,
)
from src.query_store import Q_HEALTHCHECK, Q_LIST_OPERATIONS, Filters, fetch_dataframe
from src.startup import determine_startup_context
from src.ui.components import bar_chart, line_chart, pie_chart, render_chart_section
from src.ui.comanda_details import render_comanda_expanders_from_df
from src.ui.formatting import (
    format_bs,
    format_detalle_df,
    format_int,
    format_margen_comanda_df,
    format_consumo_valorizado_df,
    format_consumo_sin_valorar_df,
    format_cogs_comanda_df,
)
from src.ui.layout import render_page_header, render_sidebar_connection_section, render_filter_context_badge


st.set_page_config(page_title="Dashback", layout="wide")


def _inject_metric_border_styles() -> None:
    st.markdown(
        """
<style>
    /*
        Bordes diferenciados por grupo de métricas.
        Nota: Streamlit no expone color de borde por API en st.metric; se controla vía CSS.
    */
    .metric-scope div[data-testid="stMetric"] {
        border-radius: 10px;
    }

    .metric-kpis div[data-testid="stMetric"] {
        border: 1px solid rgba(46, 134, 222, 0.95) !important; /* azul */
        box-shadow: 0 0 0 1px rgba(46, 134, 222, 0.10) inset;
    }

    .metric-diagnostico-impresion div[data-testid="stMetric"] {
        border: 1px solid rgba(142, 68, 173, 0.95) !important; /* morado */
        box-shadow: 0 0 0 1px rgba(142, 68, 173, 0.10) inset;
    }

    .metric-estado-operativo div[data-testid="stMetric"] {
        border: 1px solid rgba(230, 126, 34, 0.95) !important; /* naranja */
        box-shadow: 0 0 0 1px rgba(230, 126, 34, 0.10) inset;
    }
</style>
        """,
        unsafe_allow_html=True,
    )

render_page_header()
probar, connection_name = render_sidebar_connection_section()

_inject_metric_border_styles()


with st.sidebar:
    st.header("Debug")
    debug_sql = st.checkbox("Mostrar SQL/params en errores", value=False)
    ventas_use_impresion_log = st.checkbox(
        "Ventas: usar log de impresión",
        value=False,
        help=(
            "Si está activo, ventas/gráficos se calculan aceptando IMPRESO cuando la vista lo marca como IMPRESO "
            "o cuando vw_comanda_ultima_impresion indica IMPRESO. Útil cuando bar_comanda.estado_impresion queda NULL."
        ),
    )
    
    st.divider()
    st.header("Gráficos")
    limit_top_productos = st.number_input(
        "Límite top productos",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        help="Número máximo de productos en el ranking",
    )
    limit_top_usuarios = st.number_input(
        "Límite ventas por usuario",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        help="Número máximo de usuarios en el ranking",
    )
    
    grafico_categoria = st.radio(
        "Gráfico de categorías",
        ["Barras", "Torta"],
        index=0,
        help="Tipo de visualización para ventas por categoría",
    )
    
    mostrar_promedio_hora = st.checkbox(
        "Mostrar promedio en ventas por hora",
        value=True,
        help="Agrega línea horizontal con el promedio de ventas por hora",
    )


def _maybe_render_sql_debug(exc: Exception) -> None:
    if not debug_sql:
        return
    if not isinstance(exc, QueryExecutionError):
        return

    st.divider()
    st.subheader("Debug SQL")
    st.caption("SQL")
    st.code(exc.sql, language="sql")
    st.caption("Params")
    st.json(exc.params)


conn = None
startup = None
filters = Filters()
mode_for_metrics = "none"

try:
    conn = get_connection(connection_name)
    startup = determine_startup_context(conn)

    if startup.mode == "realtime":
        with st.sidebar:
            st.header("Tiempo real")
            st.button("Actualizar", help="Vuelve a consultar la base y refresca el dashboard")

    if startup.mode == "realtime":
        st.success(startup.message)
    else:
        st.info(startup.message)

    op_txt = f"Operativa: #{startup.operacion_id}" if startup.operacion_id is not None else "Operativa: —"
    st.caption(f"Modo: {startup.mode} · {op_txt} · Vista: {startup.view_name}")

    if startup.mode == "historical":
        ops_df = fetch_dataframe(conn, Q_LIST_OPERATIONS)
        ops: list[dict] = []
        if ops_df is not None and not ops_df.empty:
            ops = ops_df.to_dict(orient="records")

        with st.sidebar:
            st.header("Histórico")
            filtro_historico = st.radio(
                "Filtrar histórico por",
                ["Operativas", "Fechas"],
                index=0,
                help=(
                    "Define cómo se acota el histórico. "
                    "Operativas filtra por id_operacion (op_ini–op_fin). "
                    "Fechas filtra por fecha_emision (dt_ini–dt_fin)."
                ),
            )

            if filtro_historico == "Fechas":
                dt_ini_date = st.date_input(
                    "Fecha inicio",
                    help=(
                        "Inicio del rango para histórico (se aplica sobre fecha_emision). "
                        "El rango se interpreta como fecha inicio 00:00:00."
                    ),
                )
                dt_fin_date = st.date_input(
                    "Fecha fin",
                    help=(
                        "Fin del rango para histórico (se aplica sobre fecha_emision). "
                        "El rango se interpreta como fecha fin 23:59:59."
                    ),
                )

                if dt_ini_date > dt_fin_date:
                    dt_ini_date, dt_fin_date = dt_fin_date, dt_ini_date

                dt_ini = f"{dt_ini_date} 00:00:00"
                dt_fin = f"{dt_fin_date} 23:59:59"

                filters = Filters(dt_ini=dt_ini, dt_fin=dt_fin)
                mode_for_metrics = "dates"
            else:
                if not ops:
                    st.info("No se encontraron operativas HAB para seleccionar.")
                else:
                    ids = [int(o["id"]) for o in ops]
                    labels = [
                        f"#{o['id']} · {o.get('estado_operacion_nombre') or o.get('estado_operacion') or ''}".strip()
                        for o in ops
                    ]

                    default_id = startup.operacion_id if startup.operacion_id in ids else ids[0]
                    default_idx = ids.index(default_id)

                    op_ini_label = st.selectbox(
                        "Operativa inicio",
                        labels,
                        index=default_idx,
                        help=(
                            "Inicio del rango de operativas para histórico. "
                            "Se aplica como filtro id_operacion BETWEEN op_ini AND op_fin."
                        ),
                    )
                    op_fin_label = st.selectbox(
                        "Operativa fin",
                        labels,
                        index=default_idx,
                        help=(
                            "Fin del rango de operativas para histórico. "
                            "Se aplica como filtro id_operacion BETWEEN op_ini AND op_fin."
                        ),
                    )

                    op_ini = ids[labels.index(op_ini_label)]
                    op_fin = ids[labels.index(op_fin_label)]
                    if op_ini > op_fin:
                        op_ini, op_fin = op_fin, op_ini

                    filters = Filters(op_ini=op_ini, op_fin=op_fin)
                    mode_for_metrics = "ops"
    else:
        if startup.operacion_id is not None:
            filters = Filters(op_ini=startup.operacion_id, op_fin=startup.operacion_id)
            mode_for_metrics = "ops"
        else:
            mode_for_metrics = "none"
except Exception as exc:
    st.warning(
        "No se pudo determinar el contexto operativo automáticamente. "
        "Usa 'Probar conexión' para validar acceso a la base de datos."
    )
    st.caption(f"Detalle: {exc}")


if probar:
    try:
        if conn is None:
            conn = get_connection(connection_name)
        df = fetch_dataframe(conn, Q_HEALTHCHECK)
        missing: list[str] = []
        db_name = None
        if df is not None and not df.empty:
            if "database_name" in df.columns:
                try:
                    db_name = df["database_name"].iloc[0]
                except Exception:
                    db_name = None
            if "object_name" in df.columns and "exists_in_db" in df.columns:
                missing = [
                    str(row["object_name"])
                    for _, row in df.iterrows()
                    if int(row.get("exists_in_db") or 0) == 0
                ]

        if missing:
            st.warning(
                "Conexión OK, pero faltan vistas/tablas requeridas en la base activa"
                + (f" ({db_name})" if db_name else "")
                + f": {', '.join(missing)}"
            )
        else:
            st.success(
                "Conexión OK"
                + (f" · Base activa: {db_name}" if db_name else "")
                + " · Vistas OK"
            )

        st.dataframe(df, width="stretch")
    except Exception as exc:
        st.error(f"Error conectando a MySQL: {exc}")

st.divider()

st.subheader("KPIs")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver KPIs.")
else:
    try:
        kpis = get_kpis(conn, startup.view_name, filters, mode_for_metrics)

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
            _maybe_render_sql_debug(exc)

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
        st.error(f"Error calculando KPIs: {exc}")
        _maybe_render_sql_debug(exc)

st.subheader("Márgenes & Rentabilidad")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver márgenes.")
else:
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
                    st.dataframe(format_margen_comanda_df(detalle_pnl), use_container_width=True)
                    
                    st.subheader("📋 Detalles de Comandas")
                    # Usar la vista de comandas base para los ítems (no vw_margen_comanda).
                    render_comanda_expanders_from_df(conn, detalle_pnl, startup.view_name)

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
                    st.dataframe(format_cogs_comanda_df(cogs_df), use_container_width=True)
                    
                    st.subheader("📋 Detalles de Comandas")
                    # Usar la vista de comandas base para los ítems (no vw_cogs_comanda).
                    render_comanda_expanders_from_df(conn, cogs_df, startup.view_name)
    except Exception as exc:
        st.error(f"Error calculando P&L: {exc}")
        _maybe_render_sql_debug(exc)

st.subheader("Estado operativo")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver estado operativo.")
else:
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
            help=(
                "Comandas no anuladas con estado_impresion='PENDIENTE' (en cola/por procesar)."
            ),
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
                    snap = get_impresion_snapshot(conn, startup.view_name, ids_all)
                    st.dataframe(snap, width="stretch")
    except Exception as exc:
        st.error(f"Error cargando estado operativo: {exc}")
        _maybe_render_sql_debug(exc)

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
        debug_fn=_maybe_render_sql_debug,
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
        debug_fn=_maybe_render_sql_debug,
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
        debug_fn=_maybe_render_sql_debug,
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
        debug_fn=_maybe_render_sql_debug,
    )

st.subheader("Detalle")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver el detalle.")
else:
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
            _maybe_render_sql_debug(exc)

st.subheader("Cómo extender")
st.write(
    "Para agregar una métrica: define el SQL en src/query_store.py, expón un servicio en src/metrics.py y cablea la UI en app.py (y/o src/ui/)."
)
