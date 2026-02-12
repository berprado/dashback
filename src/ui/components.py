from __future__ import annotations

"""Componentes de visualización para el dashboard.

Biblioteca de gráficos Plotly con formato Bolivia integrado:
- bar_chart(): Barras verticales/horizontales
- line_chart(): Líneas con marcadores y línea de promedio opcional
- pie_chart(): Gráfico de torta con porcentajes
- area_chart(): Gráfico de área para distribuciones/acumulados
- render_chart_section(): Helper unificado para renderizar gráficos con manejo de errores y exportación CSV

Todos los componentes soportan:
- Formato Bolivia (Bs 1.100,33) vía parámetro `money=True`
- Tooltips enriquecidos vía `hover_data`
- Márgenes optimizados para dashboard
"""

from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui.formatting import apply_plotly_bs


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str | None = None,
    orientation: str | None = None,
    *,
    money: bool = False,
    money_decimals: int = 2,
    hover_data: dict[str, str | bool] | None = None,
):
    """Crea un gráfico de barras (Plotly) a partir de un DataFrame.
    
    Args:
        df: DataFrame con los datos
        x: Columna para eje X
        y: Columna para eje Y
        title: Título del gráfico
        orientation: 'h' para horizontal, 'v' o None para vertical
        money: Si True, aplica formato Bolivia a valores
        money_decimals: Decimales para formato dinero
        hover_data: Dict con columnas adicionales para tooltip.
                    Keys = nombre columna, Values = formato (True para incluir, False para ocultar, string para custom)
    """
    fig = px.bar(df, x=x, y=y, title=title, orientation=orientation, hover_data=hover_data)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

    if money:
        # En barras horizontales el eje de valores es X; en vertical es Y.
        value_axis = "x" if (orientation or "").lower().startswith("h") else "y"
        apply_plotly_bs(fig, axis=value_axis, decimals=int(money_decimals))

    return fig


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str | None = None,
    *,
    money: bool = False,
    money_decimals: int = 2,
    hover_data: dict[str, str | bool] | None = None,
    markers: bool = True,
    show_average: bool = False,
):
    """Crea un gráfico de línea (Plotly) a partir de un DataFrame.
    
    Args:
        df: DataFrame con los datos
        x: Columna para eje X
        y: Columna para eje Y
        title: Título del gráfico
        money: Si True, aplica formato Bolivia a valores
        money_decimals: Decimales para formato dinero
        hover_data: Dict con columnas adicionales para tooltip
        markers: Si True, muestra marcadores en los puntos
        show_average: Si True, agrega línea horizontal con promedio
    """
    fig = px.line(df, x=x, y=y, title=title, hover_data=hover_data, markers=markers)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

    if money:
        apply_plotly_bs(fig, axis="y", decimals=int(money_decimals))
    
    # Agregar línea de promedio si se solicita
    if show_average and not df.empty:
        avg_value = df[y].mean()
        fig.add_hline(
            y=avg_value,
            line_dash="dash",
            line_color="rgba(255, 0, 0, 0.5)",
            annotation_text=f"Promedio: {avg_value:,.2f}",
            annotation_position="right",
        )

    return fig


def pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str | None = None,
    *,
    money: bool = False,
    money_decimals: int = 2,
    hover_data: list[str] | None = None,
):
    """Crea un gráfico de torta (Plotly) a partir de un DataFrame.
    
    Args:
        df: DataFrame con los datos
        names: Columna para etiquetas de las porciones
        values: Columna para valores de las porciones
        title: Título del gráfico
        money: Si True, aplica formato Bolivia a valores
        money_decimals: Decimales para formato dinero
        hover_data: Lista de columnas adicionales para tooltip
    """
    fig = px.pie(df, names=names, values=values, title=title, hover_data=hover_data)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    
    # Para pie charts, aplicar formato en hovertemplate
    if money:
        from src.ui.formatting import format_bs
        fig.update_traces(
            texttemplate='%{label}<br>%{percent}',
            hovertemplate='<b>%{label}</b><br>%{value:,.2f}<extra></extra>',
        )

    return fig


def area_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str | None = None,
    *,
    money: bool = False,
    money_decimals: int = 2,
    hover_data: dict[str, str | bool] | None = None,
):
    """Crea un gráfico de área (Plotly) a partir de un DataFrame.
    
    Útil para mostrar distribuciones o valores acumulados.
    
    Args:
        df: DataFrame con los datos
        x: Columna para eje X
        y: Columna para eje Y
        title: Título del gráfico
        money: Si True, aplica formato Bolivia a valores
        money_decimals: Decimales para formato dinero
        hover_data: Dict con columnas adicionales para tooltip
    """
    fig = px.area(df, x=x, y=y, title=title, hover_data=hover_data)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

    if money:
        apply_plotly_bs(fig, axis="y", decimals=int(money_decimals))

    return fig


def render_chart_section(
    title: str,
    caption: str,
    data_fn: Callable[[], pd.DataFrame | None],
    chart_fn: Callable[[pd.DataFrame], Any],
    *,
    conn: Any = None,
    startup: Any = None,
    debug_fn: Callable[[Exception], None] | None = None,
    empty_msg: str = "Sin datos para el rango seleccionado.",
    check_realtime_empty: bool = False,
    allow_csv_export: bool = True,
    fallback_data: pd.DataFrame | None = None,
    show_retry: bool = True,
    fallback_key: str | None = None,
) -> None:
    """Helper para renderizar secciones de gráficos con patrón unificado.
    
    Args:
        title: Título de la sección (subheader)
        caption: Descripción del gráfico
        data_fn: Función sin args que retorna DataFrame (ya preparada con partial/lambda)
        chart_fn: Función que recibe DataFrame y retorna figura Plotly
        conn: Conexión a DB (si None, muestra mensaje de conexión)
        startup: Objeto de startup (para validar modo realtime)
        debug_fn: Función opcional para renderizar debug SQL
        empty_msg: Mensaje cuando no hay datos
        check_realtime_empty: Si True, distingue entre realtime sin datos vs filtro vacío
        allow_csv_export: Si True, muestra botón de descarga CSV
    """
    st.subheader(title)
    st.caption(caption)
    
    if conn is None or startup is None:
        st.info(f"Conecta a la base de datos para ver {title.lower()}.")
        return
    
    try:
        df = data_fn()

        if df is None or df.empty:
            if check_realtime_empty and startup.mode == "realtime" and not startup.has_rows:
                st.info("Aún no se registraron ventas en esta operativa.")
            else:
                st.info(empty_msg)
        else:
            if fallback_key:
                st.session_state[f"chart_fallback_{fallback_key}"] = df.copy()
            fig = chart_fn(df)
            st.plotly_chart(fig, width="stretch")
            
            # Botón de exportación CSV
            if allow_csv_export:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=":material/download: Descargar CSV",
                    data=csv_data,
                    file_name=f"{title.lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"csv_{title.lower().replace(' ', '_')}",
                )
    except Exception as exc:
        st.warning(f"No se pudo cargar {title.lower()}.")
        with st.expander("Ver detalles del error", expanded=False):
            st.error(str(exc))
            if debug_fn:
                debug_fn(exc)
        if show_retry:
            if st.button(
                f"Reintentar {title}",
                key=f"retry_{title.lower().replace(' ', '_')}",
            ):
                st.rerun()
        if fallback_data is None and fallback_key:
            fallback_data = st.session_state.get(f"chart_fallback_{fallback_key}")
        if fallback_data is not None and not fallback_data.empty:
            st.caption("Mostrando datos en cache (último cálculo exitoso).")
            st.dataframe(fallback_data, width="stretch")
