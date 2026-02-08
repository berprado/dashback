from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _to_finite_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0

    if math.isnan(x) or math.isinf(x):
        return 0.0
    return x


def _format_number_es(value: float, *, decimals: int) -> str:
    """Formatea un número usando convención es/LatAm.

    - Miles con punto: 1.100
    - Decimales con coma: 1.100,33

    Nota: no depende del locale del sistema operativo.
    """

    s = f"{value:,.{int(decimals)}f}"  # 1,100.33
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def format_bs(value: Any, *, decimals: int = 2) -> str:
    """Formatea montos en Bolivianos.

    Formato acordado: `Bs 1.100,33`.
    """

    x = _to_finite_float(value)
    sign = "-" if x < 0 else ""
    return f"{sign}Bs {_format_number_es(abs(x), decimals=decimals)}"


def format_int(value: Any) -> str:
    """Formatea conteos con separador de miles (punto)."""

    x = _to_finite_float(value)
    try:
        n = int(round(x))
    except Exception:
        n = 0

    sign = "-" if n < 0 else ""
    n = abs(n)
    return f"{sign}{n:,}".replace(",", ".")


# --- Plotly helpers (formato Bolivia) ---

# Plotly/D3 usan `layout.separators` con (decimal, miles). Para Bolivia:
# - decimal: ','
# - miles: '.'
PLOTLY_SEPARATORS_BO = ',.'


def apply_plotly_bs(fig: Any, *, axis: str = "y", decimals: int = 2) -> None:
    """Aplica formato de dinero Bolivia (Bs + separadores) a un gráfico Plotly.

    Centraliza el estilo para que ejes y tooltips coincidan con `format_bs`.
    """

    try:
        fig.update_layout(separators=PLOTLY_SEPARATORS_BO)
    except Exception:
        pass


def format_df_money_columns(df: pd.DataFrame, money_columns: list[str], *, decimals: int = 2) -> pd.DataFrame:
    """Devuelve una copia del DataFrame con columnas monetarias formateadas como string.

    Motivo: `st.dataframe` es muy flexible, pero el formateo por locale puede variar.
    Convirtiendo a string aseguramos consistencia: `Bs 1.100,33`.

    Nota: al convertir a string, el ordenamiento por columna pasa a ser lexicográfico.
    Para la tabla de "Detalle" (inspección) es un trade-off aceptable.
    """

    if df is None or df.empty:
        return df

    out = df.copy()
    for col in money_columns:
        if col in out.columns:
            out[col] = out[col].apply(lambda v: format_bs(v, decimals=decimals))
    return out


def format_detalle_df(df: pd.DataFrame) -> pd.DataFrame:
    """Formatea el DataFrame de detalle para visualización en Streamlit."""

    return format_df_money_columns(df, ["precio_venta", "sub_total"], decimals=2)


def format_margen_comanda_df(df: pd.DataFrame) -> pd.DataFrame:
    """Formatea el DataFrame de margen por comanda para visualización en Streamlit."""

    return format_df_money_columns(df, ["total_venta", "cogs_comanda", "margen_comanda"], decimals=2)


def format_number(value: Any, *, decimals: int = 2) -> str:
    """Formatea un número con separador de miles (punto) y decimales (coma).

    Sin prefijo monetario. Útil para cantidades, precios unitarios, etc.
    """

    x = _to_finite_float(value)
    sign = "-" if x < 0 else ""
    return f"{sign}{_format_number_es(abs(x), decimals=decimals)}"


def format_consumo_valorizado_df(df: pd.DataFrame) -> pd.DataFrame:
    """Formatea el DataFrame de consumo valorizado para visualización en Streamlit."""

    if df is None or df.empty:
        return df

    out = df.copy()
    
    # Cantidades con 4 decimales
    if "cantidad_consumida_base" in out.columns:
        out["cantidad_consumida_base"] = out["cantidad_consumida_base"].apply(
            lambda v: format_number(v, decimals=4)
        )
    
    # Monetarios con 2 decimales
    money_cols = ["wac_operativa", "costo_consumo"]
    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda v: format_bs(v, decimals=2))
    
    return out


def format_consumo_sin_valorar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Formatea el DataFrame de consumo sin valorar para visualización en Streamlit."""

    if df is None or df.empty:
        return df

    out = df.copy()
    
    # Solo cantidades con 4 decimales (sin montos)
    if "cantidad_consumida_base" in out.columns:
        out["cantidad_consumida_base"] = out["cantidad_consumida_base"].apply(
            lambda v: format_number(v, decimals=4)
        )
    
    return out

    axis = (axis or "y").lower().strip()
    if axis not in {"x", "y"}:
        axis = "y"

    tickformat = f",.{int(decimals)}f"
    try:
        if axis == "x":
            fig.update_xaxes(tickprefix="Bs ", tickformat=tickformat)
        else:
            fig.update_yaxes(tickprefix="Bs ", tickformat=tickformat)
    except Exception:
        pass

    # Hover: usa d3-format; con separators=',.' se renderiza como 1.100,33.
    try:
        var = "x" if axis == "x" else "y"
        fig.update_traces(hovertemplate=f"%{{{var}:{tickformat}}}<extra></extra>")
        # Nota: el prefijo 'Bs ' en hover lo agrega tickprefix en algunos casos,
        # pero no siempre; por eso lo incluimos explícito.
        fig.update_traces(hovertemplate=f"Bs %{{{var}:{tickformat}}}<extra></extra>")
    except Exception:
        pass
