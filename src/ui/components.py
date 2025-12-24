from __future__ import annotations

import pandas as pd
import plotly.express as px


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str | None = None,
    orientation: str | None = None,
):
    """Crea un gráfico de barras (Plotly) a partir de un DataFrame."""
    fig = px.bar(df, x=x, y=y, title=title, orientation=orientation)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig
