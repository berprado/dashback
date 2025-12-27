from __future__ import annotations

import pandas as pd
import plotly.express as px

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
):
    """Crea un gráfico de barras (Plotly) a partir de un DataFrame."""
    fig = px.bar(df, x=x, y=y, title=title, orientation=orientation)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

    if money:
        # En barras horizontales el eje de valores es X; en vertical es Y.
        value_axis = "x" if (orientation or "").lower().startswith("h") else "y"
        apply_plotly_bs(fig, axis=value_axis, decimals=int(money_decimals))

    return fig
