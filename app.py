from __future__ import annotations

import streamlit as st

from src.db import get_connection
from src.metrics import (
    QueryExecutionError,
    get_actividad_emision_comandas,
    get_detalle,
    get_estado_operativo,
    get_ids_comandas_no_impresas,
    get_ids_comandas_pendientes,
    get_kpis,
    get_top_productos,
    get_ventas_por_categoria,
    get_ventas_por_hora,
    get_ventas_por_usuario,
)
from src.query_store import Q_HEALTHCHECK, Q_LIST_OPERATIONS, Filters, fetch_dataframe
from src.startup import determine_startup_context
from src.ui.components import bar_chart
from src.ui.layout import render_page_header, render_sidebar_connection_section


st.set_page_config(page_title="Dashback", layout="wide")

render_page_header()
probar, connection_name = render_sidebar_connection_section()


with st.sidebar:
    st.header("Debug")
    debug_sql = st.checkbox("Mostrar SQL/params en errores", value=False)


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
            )

            if filtro_historico == "Fechas":
                dt_ini_date = st.date_input("Fecha inicio")
                dt_fin_date = st.date_input("Fecha fin")

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

                    op_ini_label = st.selectbox("Operativa inicio", labels, index=default_idx)
                    op_fin_label = st.selectbox("Operativa fin", labels, index=default_idx)

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
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Total vendido",
            f"{kpis['total_vendido']:.2f}",
            help="Suma de sub_total (ventas) en el rango/vista seleccionada.",
            border=True,
        )
        c2.metric(
            "Comandas",
            f"{kpis['total_comandas']}",
            help="Cantidad de comandas distintas (COUNT DISTINCT id_comanda).",
            border=True,
        )
        c3.metric(
            "Ítems",
            f"{kpis['items_vendidos']:.0f}",
            help="Suma de cantidades (SUM cantidad).",
            border=True,
        )
        c4.metric(
            "Ticket promedio",
            f"{kpis['ticket_promedio']:.2f}",
            help="Total vendido / comandas (redondeado).",
            border=True,
        )

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

            a1, a2, a3, a4 = st.columns(4)
            a1.metric(
                "Última comanda",
                last_ts_txt,
                help="Hora (MAX fecha_emision) de la última comanda emitida en el contexto actual.",
                border=True,
            )
            a2.metric(
                "Min desde última",
                minutes_since_txt,
                help="Minutos transcurridos desde la última comanda (según reloj del servidor).",
                border=True,
            )
            a3.metric(
                f"Ritmo (últimas {int(recent_n or 10)})",
                (f"{float(recent_median):.1f} min" if recent_median is not None else None),
                help=(
                    "Mediana de minutos entre comandas consecutivas (por id_comanda). "
                    + (f"Intervalos usados: {int(recent_intervals or 0)}.")
                ),
                border=True,
            )
            a4.metric(
                "Ritmo (operativa/rango)",
                (f"{float(all_median):.1f} min" if all_median is not None else None),
                help=(
                    "Mediana de minutos entre comandas consecutivas en todo el contexto actual. "
                    + (f"Intervalos usados: {int(all_intervals or 0)}.")
                ),
                border=True,
            )
        except Exception as exc:
            st.warning(f"No se pudo calcular actividad: {exc}")
            _maybe_render_sql_debug(exc)

        k1, k2, k3 = st.columns(3)
        k1.metric(
            "Total cortesías",
            f"{kpis['total_cortesia']:.2f}",
            help="Para tipo_salida=CORTESIA usa cor_subtotal_anterior cuando aplica.",
            border=True,
        )
        k2.metric(
            "Comandas cortesía",
            f"{kpis['comandas_cortesia']}",
            help="Cantidad de comandas con tipo_salida=CORTESIA.",
            border=True,
        )
        k3.metric(
            "Ítems cortesía",
            f"{kpis['items_cortesia']:.0f}",
            help="Suma de cantidad donde tipo_salida=CORTESIA.",
            border=True,
        )
    except Exception as exc:
        st.error(f"Error calculando KPIs: {exc}")
        _maybe_render_sql_debug(exc)

st.subheader("Estado operativo")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver estado operativo.")
else:
    try:
        estado = get_estado_operativo(conn, startup.view_name, filters, mode_for_metrics)
        e1, e2 = st.columns(2)
        e1.metric(
            "Comandas pendientes",
            f"{estado['comandas_pendientes']}",
            help="COUNT DISTINCT id_comanda con estado_comanda='PENDIENTE'.",
            border=True,
        )
        e2.metric(
            "Comandas no impresas",
            f"{estado['comandas_no_impresas']}",
            help="COUNT DISTINCT id_comanda donde estado_impresion es NULL o <> 'IMPRESO'.",
            border=True,
        )

        with st.expander("Ver IDs de comandas (pendientes / no impresas)", expanded=False):
            cargar_ids = st.checkbox("Cargar IDs", value=False, key="estado_operativo_load_ids")
            limit = st.number_input("Límite", min_value=10, max_value=200, value=50, step=10)

            if cargar_ids:
                ids_pend = get_ids_comandas_pendientes(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )
                ids_noimp = get_ids_comandas_no_impresas(
                    conn,
                    startup.view_name,
                    filters,
                    mode_for_metrics,
                    limit=int(limit),
                )

                i1, i2 = st.columns(2)
                i1.caption("Pendientes")
                i1.caption(f"Mostrando {len(ids_pend)} (límite {int(limit)})")
                i1.code(", ".join(map(str, ids_pend)) if ids_pend else "—")
                i2.caption("No impresas")
                i2.caption(f"Mostrando {len(ids_noimp)} (límite {int(limit)})")
                i2.code(", ".join(map(str, ids_noimp)) if ids_noimp else "—")
    except Exception as exc:
        st.error(f"Error cargando estado operativo: {exc}")
        _maybe_render_sql_debug(exc)

g1, g2 = st.columns(2)

with g1:
    st.subheader("Ventas por hora")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver ventas por hora.")
    else:
        try:
            por_hora = get_ventas_por_hora(conn, startup.view_name, filters, mode_for_metrics)
            if por_hora is None or por_hora.empty:
                if startup.mode == "realtime" and not startup.has_rows:
                    st.info("Aún no se registraron ventas en esta operativa.")
                else:
                    st.info("Sin datos para el rango seleccionado.")
            else:
                fig = bar_chart(por_hora, x="hora", y="total_vendido", title=None)
                st.plotly_chart(fig, width="stretch")
        except Exception as exc:
            st.error(f"Error cargando ventas por hora: {exc}")
            _maybe_render_sql_debug(exc)

with g2:
    st.subheader("Ventas por categoría")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver ventas por categoría.")
    else:
        try:
            por_categoria = get_ventas_por_categoria(conn, startup.view_name, filters, mode_for_metrics)
            if por_categoria is None or por_categoria.empty:
                st.info("Sin datos para el rango seleccionado.")
            else:
                fig = bar_chart(por_categoria, x="categoria", y="total_vendido", title=None)
                st.plotly_chart(fig, width="stretch")
        except Exception as exc:
            st.error(f"Error cargando ventas por categoría: {exc}")
            _maybe_render_sql_debug(exc)

g3, g4 = st.columns(2)

with g3:
    st.subheader("Top productos")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver top productos.")
    else:
        try:
            top = get_top_productos(conn, startup.view_name, filters, mode_for_metrics, limit=20)
            if top is None or top.empty:
                st.info("Sin datos para el rango seleccionado.")
            else:
                fig = bar_chart(top, x="total_vendido", y="nombre", title=None, orientation="h")
                st.plotly_chart(fig, width="stretch")
        except Exception as exc:
            st.error(f"Error cargando top productos: {exc}")
            _maybe_render_sql_debug(exc)

with g4:
    st.subheader("Ventas por usuario")
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver ventas por usuario.")
    else:
        try:
            por_usuario = get_ventas_por_usuario(conn, startup.view_name, filters, mode_for_metrics, limit=20)
            if por_usuario is None or por_usuario.empty:
                st.info("Sin datos para el rango seleccionado.")
            else:
                fig = bar_chart(por_usuario, x="total_vendido", y="usuario_reg", title=None, orientation="h")
                st.plotly_chart(fig, width="stretch")
        except Exception as exc:
            st.error(f"Error cargando ventas por usuario: {exc}")
            _maybe_render_sql_debug(exc)

st.subheader("Detalle")
if conn is None or startup is None:
    st.info("Conecta a la base de datos para ver el detalle.")
else:
    with st.expander("Ver detalle (últimas 500 filas)", expanded=False):
        cargar_detalle = st.checkbox("Cargar detalle", value=False, key="detalle_load")
        try:
            if cargar_detalle:
                detalle = get_detalle(conn, startup.view_name, filters, mode_for_metrics, limit=500)
                if detalle is None or detalle.empty:
                    st.info("Sin datos para el rango seleccionado.")
                else:
                    st.dataframe(detalle, width="stretch")
        except Exception as exc:
            st.error(f"Error cargando detalle: {exc}")
            _maybe_render_sql_debug(exc)

st.subheader("Siguiente paso")
st.write(
    "Agrega consultas en `src/query_store.py` y UI en `src/ui/` para construir el dashboard."
)
