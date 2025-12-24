from __future__ import annotations

import streamlit as st

from config.database import get_connection
from data.queries import Q_HEALTHCHECK, fetch_dataframe


st.set_page_config(page_title="Dashback", layout="wide")

st.title("Dashback")
st.caption("Dashboard base con conexión MySQL")

with st.sidebar:
    st.header("Conexión")
    st.write("Configura `.env` con DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.")
    probar = st.button("Probar conexión")


@st.cache_resource(show_spinner=False)
def _get_conn_cached():
    return get_connection()


if probar:
    try:
        conn = _get_conn_cached()
        df = fetch_dataframe(conn, Q_HEALTHCHECK)
        st.success("Conexión OK")
        st.dataframe(df, use_container_width=True)
    except Exception as exc:
        st.error(f"Error conectando a MySQL: {exc}")

st.divider()

st.subheader("Siguiente paso")
st.write(
    "Agrega consultas en `data/queries.py` y componentes en `components/` para construir el dashboard."
)
