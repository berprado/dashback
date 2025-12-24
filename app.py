from __future__ import annotations

import streamlit as st

from config.database import get_connection
from data.queries import Q_HEALTHCHECK, fetch_dataframe


st.set_page_config(page_title="Dashback", layout="wide")

st.title("Dashback")
st.caption("Dashboard base con conexión MySQL")

with st.sidebar:
    st.header("Conexión")
    st.write("Configura `.streamlit/secrets.toml` con `[connections.mysql]`.")
    probar = st.button("Probar conexión")


if probar:
    try:
        conn = get_connection()
        df = fetch_dataframe(conn, Q_HEALTHCHECK)
        st.success("Conexión OK")
        st.dataframe(df, width="stretch")
    except Exception as exc:
        st.error(f"Error conectando a MySQL: {exc}")

st.divider()

st.subheader("Siguiente paso")
st.write(
    "Agrega consultas en `data/queries.py` y componentes en `components/` para construir el dashboard."
)
