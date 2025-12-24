from __future__ import annotations

import streamlit as st


def render_page_header() -> None:
    st.title("Dashback")
    st.caption("Dashboard base con conexión MySQL")


def render_sidebar_connection_section() -> bool:
    with st.sidebar:
        st.header("Conexión")
        st.write("Configura `.streamlit/secrets.toml` (o `.streamlit/secrets.toml.example`).")
        return st.button("Probar conexión")
