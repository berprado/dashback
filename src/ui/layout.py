from __future__ import annotations

from typing import Any

import streamlit as st


def render_page_header() -> None:
    st.markdown("# :material/insights: Dashback")
    st.caption("Dashboard base con conexión MySQL")


def render_sidebar_connection_section() -> tuple[bool, str]:
    with st.sidebar:
        st.header(":material/lan: Conexión")

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
            parts.append(f":material/insights: Op. {filters.op_ini}")
        else:
            parts.append(f":material/insights: Op. {filters.op_ini}-{filters.op_fin}")
    elif mode == "dates" and filters.dt_ini and filters.dt_fin:
        dt_ini_short = filters.dt_ini[:10] if len(filters.dt_ini) >= 10 else filters.dt_ini
        dt_fin_short = filters.dt_fin[:10] if len(filters.dt_fin) >= 10 else filters.dt_fin
        parts.append(f":material/date_range: {dt_ini_short} → {dt_fin_short}")
    elif mode == "none":
        parts.append(":material/timelapse: Tiempo real")
    
    # Estado del toggle de impresión
    if use_impresion_log:
        parts.append(":material/print: Log impresión: ON")
    
    if parts:
        badge_text = " • ".join(parts)
        # Usamos st.markdown estándar para asegurar que los iconos Material Symbols se rendericen.
        # Envolvemos en un contenedor con borde para darle presencia visual similar a un badge.
        with st.container(border=True):
            st.markdown(badge_text, help="Contexto de filtros aplicado actualmente.")
