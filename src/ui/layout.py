from __future__ import annotations

import streamlit as st


def render_page_header() -> None:
    st.title("Dashback")
    st.caption("Dashboard base con conexión MySQL")


def render_sidebar_connection_section() -> tuple[bool, str]:
    with st.sidebar:
        st.header("Conexión")
        st.write("Configura `.streamlit/secrets.toml` (o `.streamlit/secrets.toml.example`).")

        connection_options: list[tuple[str, str]] = [("Local", "mysql")]
        try:
            if "connections" in st.secrets and "mysql_prod" in st.secrets["connections"]:
                connection_options.append(("Producción", "mysql_prod"))
        except Exception:
            pass

        labels = [label for label, _ in connection_options]
        values = [value for _, value in connection_options]

        default_value = st.session_state.get("connection_name", values[0])
        if default_value not in values:
            default_value = values[0]

        selected_label = st.selectbox(
            "Origen de datos",
            labels,
            index=values.index(default_value),
        )
        connection_name = values[labels.index(selected_label)]
        st.session_state["connection_name"] = connection_name

        probar = st.button("Probar conexión")
        return probar, connection_name
