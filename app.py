from __future__ import annotations

import streamlit as st

from src.db import get_connection
from src.query_store import Q_HEALTHCHECK, fetch_dataframe
from src.startup import determine_startup_context
from src.ui.layout import render_page_header, render_sidebar_connection_section


st.set_page_config(page_title="Dashback", layout="wide")

render_page_header()
probar = render_sidebar_connection_section()


conn = None

try:
    conn = get_connection()
    startup = determine_startup_context(conn)

    if startup.mode == "realtime":
        st.success(startup.message)
    else:
        st.info(startup.message)

    st.caption(f"Modo: {startup.mode} · Vista: {startup.view_name}")
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

st.subheader("Siguiente paso")
st.write(
    "Agrega consultas en `src/query_store.py` y UI en `src/ui/` para construir el dashboard."
)
