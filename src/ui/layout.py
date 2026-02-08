from __future__ import annotations

from typing import Any

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


def render_filter_context_badge(
    filters: Any,
    mode: str,
    use_impresion_log: bool = False,
) -> None:
    """Renderiza un badge visual con el contexto de filtros aplicados.
    
    Args:
        filters: Objeto Filters con op_ini/op_fin o dt_ini/dt_fin
        mode: 'none', 'ops' o 'dates'
        use_impresion_log: Si True, indica que el log de impresión está activo
    """
    parts = []
    
    # Contexto de filtro
    if mode == "ops" and filters.op_ini and filters.op_fin:
        if filters.op_ini == filters.op_fin:
            parts.append(f"📋 Op. {filters.op_ini}")
        else:
            parts.append(f"📋 Op. {filters.op_ini}-{filters.op_fin}")
    elif mode == "dates" and filters.dt_ini and filters.dt_fin:
        dt_ini_short = filters.dt_ini[:10] if len(filters.dt_ini) >= 10 else filters.dt_ini
        dt_fin_short = filters.dt_fin[:10] if len(filters.dt_fin) >= 10 else filters.dt_fin
        parts.append(f"📅 {dt_ini_short} → {dt_fin_short}")
    elif mode == "none":
        parts.append("⏱️ Tiempo real")
    
    # Estado del toggle de impresión
    if use_impresion_log:
        parts.append("📦 Log impresión: ON")
    
    if parts:
        badge_text = " • ".join(parts)
        st.markdown(
            f'<div style="background-color: #f0f2f6; color: #262730; padding: 8px 12px; '
            f'border-radius: 4px; margin-bottom: 12px; font-size: 14px; '
            f'text-align: center;">{badge_text}</div>',
            unsafe_allow_html=True,
        )
