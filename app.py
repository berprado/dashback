from __future__ import annotations

import streamlit as st

from src.db import get_connection
from src.metrics import QueryExecutionError
from src.query_store import Q_HEALTHCHECK, Q_LIST_OPERATIONS, Filters, fetch_dataframe
from src.startup import determine_startup_context
from src.ui.layout import render_page_header, render_sidebar_connection_section
from src.ui.sections.charts import render_charts_section
from src.ui.sections.detalle import render_detalle_section
from src.ui.sections.estado import render_estado_operativo_section
from src.ui.sections.kpis import render_kpis_section
from src.ui.sections.margenes import render_margenes_section


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
        border-radius: 12px;
        background: #0F1624;
        padding: 6px;
    }

    .metric-scope div[data-testid="stMetric"] > div {
        padding: 10px 12px;
    }

    .metric-kpis div[data-testid="stMetric"] {
        border: 1px solid rgba(59, 130, 246, 0.9) !important; /* azul */
        box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.15) inset;
    }

    .metric-diagnostico-impresion div[data-testid="stMetric"] {
        border: 1px solid rgba(168, 85, 247, 0.9) !important; /* violeta */
        box-shadow: 0 0 0 1px rgba(168, 85, 247, 0.15) inset;
    }

    .metric-estado-operativo div[data-testid="stMetric"] {
        border: 1px solid rgba(249, 115, 22, 0.9) !important; /* naranja */
        box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.15) inset;
    }
</style>
        """,
        unsafe_allow_html=True,
    )

render_page_header()
probar, connection_name = render_sidebar_connection_section()

_inject_metric_border_styles()


with st.sidebar:
    st.header(":material/bug_report: Debug")
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
    st.header(":material/bar_chart: Gráficos")
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
            st.header(":material/timelapse: Tiempo real")
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
            st.header(":material/history: Histórico")
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

render_kpis_section(
    conn=conn,
    startup=startup,
    filters=filters,
    mode_for_metrics=mode_for_metrics,
    ventas_use_impresion_log=ventas_use_impresion_log,
    debug_fn=_maybe_render_sql_debug,
)

render_margenes_section(
    conn=conn,
    startup=startup,
    filters=filters,
    mode_for_metrics=mode_for_metrics,
    debug_fn=_maybe_render_sql_debug,
)

render_estado_operativo_section(
    conn=conn,
    startup=startup,
    filters=filters,
    mode_for_metrics=mode_for_metrics,
    debug_fn=_maybe_render_sql_debug,
)

render_charts_section(
    conn=conn,
    startup=startup,
    filters=filters,
    mode_for_metrics=mode_for_metrics,
    ventas_use_impresion_log=ventas_use_impresion_log,
    grafico_categoria=grafico_categoria,
    limit_top_productos=int(limit_top_productos),
    limit_top_usuarios=int(limit_top_usuarios),
    mostrar_promedio_hora=mostrar_promedio_hora,
    debug_fn=_maybe_render_sql_debug,
)

render_detalle_section(
    conn=conn,
    startup=startup,
    filters=filters,
    mode_for_metrics=mode_for_metrics,
    debug_fn=_maybe_render_sql_debug,
)

st.subheader("Cómo extender")
st.write(
    "Para agregar una métrica: define el SQL en src/query_store.py, expón un servicio en src/metrics.py y cablea la UI en app.py (y/o src/ui/)."
)
