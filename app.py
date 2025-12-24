from __future__ import annotations

import streamlit as st

from src.db import get_connection
from src.metrics import get_kpis, get_ventas_por_hora
from src.query_store import Q_HEALTHCHECK, Q_LIST_OPERATIONS, Filters, fetch_dataframe
from src.startup import determine_startup_context
from src.ui.components import bar_chart
from src.ui.layout import render_page_header, render_sidebar_connection_section


st.set_page_config(page_title="Dashback", layout="wide")

render_page_header()
probar = render_sidebar_connection_section()


conn = None
startup = None
filters = Filters()
mode_for_metrics = "none"

try:
    conn = get_connection()
    startup = determine_startup_context(conn)

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
            conn = get_connection()
        df = fetch_dataframe(conn, Q_HEALTHCHECK)
        st.success("Conexión OK")
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
        c1.metric("Total vendido", f"{kpis['total_vendido']:.2f}")
        c2.metric("Comandas", f"{kpis['total_comandas']}")
        c3.metric("Ítems", f"{kpis['items_vendidos']:.0f}")
        c4.metric("Ticket promedio", f"{kpis['ticket_promedio']:.2f}")
    except Exception as exc:
        st.error(f"Error calculando KPIs: {exc}")

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
            st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.error(f"Error cargando ventas por hora: {exc}")

st.subheader("Siguiente paso")
st.write(
    "Agrega consultas en `src/query_store.py` y UI en `src/ui/` para construir el dashboard."
)
