"""Componentes para mostrar detalles de comandas en expanders.

Proporciona funciones para renderizar información detallada de comandas
en expandibles, incluyendo ítems consumidos y estado operativo.
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.metrics import get_items_por_comanda
from src.ui.formatting import format_bs, format_number


def render_comanda_expander(
    conn: Any,
    row: dict[str, Any],
    view_name: str,
    *,
    mode: str = "none",
    key_suffix: str | None = None,
) -> None:
    """Renderiza un expander con detalles de una comanda específica.

    Args:
        conn: Conexión a la base de datos
        row: Fila del DataFrame con información de la comanda
        view_name: Nombre de la vista (para obtener ítems)
    """

    id_comanda = int(row.get("id_comanda", 0))
    id_mesa = row.get("id_mesa", "N/A")
    usuario = row.get("usuario_reg", "N/A")
    estado = row.get("estado_comanda", "N/A")
    fecha_emision = row.get("fecha_emision")
    total_venta = row.get("total_venta")
    cogs = row.get("cogs_comanda")
    margen = row.get("margen_comanda")

    # Encabezado del expander
    header = f":material/clipboard: Comanda {id_comanda}"
    if fecha_emision:
        try:
            ts = pd.to_datetime(fecha_emision, errors="coerce")
            if pd.notna(ts):
                header += f" | {ts.strftime('%Y-%m-%d %H:%M')}"
        except Exception:
            pass
    if usuario:
        header += f" | {usuario}"

    with st.expander(header, expanded=False):
        # Info contextual
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mesa", id_mesa)
        with col2:
            st.metric("Usuario", usuario)
        with col3:
            st.metric("Estado", estado)

        st.divider()

        # Financiero (si aplica)
        if total_venta is not None or cogs is not None or margen is not None:
            st.subheader("Resumen Financiero")
            fin_col1, fin_col2, fin_col3 = st.columns(3)

            with fin_col1:
                st.metric(
                    "Ventas",
                    format_bs(total_venta, decimals=2) if total_venta else "—",
                )
            with fin_col2:
                st.metric(
                    "COGS",
                    format_bs(cogs, decimals=2) if cogs else "—",
                )
            with fin_col3:
                st.metric(
                    "Margen",
                    format_bs(margen, decimals=2) if margen else "—",
                )

            st.divider()

        # Ítems de la comanda
        st.subheader("Ítems Consumidos")
        try:
            key = f"items_load_{id_comanda}"
            if key_suffix:
                key = f"{key}_{key_suffix}"
            cargar_items = st.checkbox(
                "Cargar ítems",
                value=False,
                key=key,
                help="Ejecuta la consulta de ítems solo bajo demanda.",
            )
            if not cargar_items:
                st.info("Activa 'Cargar ítems' para consultar el detalle.")
                return

            items_df = get_items_por_comanda(conn, view_name, id_comanda, mode=mode)

            if items_df is not None and not items_df.empty:
                # Formatear DataFrame
                items_display = items_df.copy()

                # Formatear montos
                for col in ["precio_venta", "sub_total"]:
                    if col in items_display.columns:
                        items_display[col] = items_display[col].apply(
                            lambda v: format_bs(v, decimals=2) if v else "—"
                        )

                # Formatear cantidades
                if "cantidad" in items_display.columns:
                    items_display["cantidad"] = items_display["cantidad"].apply(
                        lambda v: format_number(v, decimals=2) if v else "—"
                    )

                # Reordenar columnas para máxima legibilidad
                cols_order = [
                    "nombre_producto",
                    "cantidad",
                    "precio_venta",
                    "sub_total",
                    "categoria",
                ]
                cols_present = [c for c in cols_order if c in items_display.columns]
                cols_remaining = [c for c in items_display.columns if c not in cols_present]
                items_display = items_display[cols_present + cols_remaining]

                st.dataframe(
                    items_display,
                    width="stretch",
                    hide_index=True,
                )

                # Totales
                st.caption(
                    f"**Total ítems:** {len(items_df)} | "
                    f"**Subtotal:** {format_bs(items_df['sub_total'].sum(), decimals=2)}"
                )
            else:
                st.info("No hay ítems registrados para esta comanda.")

        except Exception as e:
            st.error(f"Error al cargar ítems: {str(e)}")


def render_comanda_expanders_from_df(
    conn: Any,
    df: pd.DataFrame,
    view_name: str,
    mode: str,
) -> None:
    """Renderiza expanders para cada comanda en un DataFrame.

    Args:
        conn: Conexión a la base de datos
        df: DataFrame con comandas (debe incluir id_comanda, id_mesa, usuario_reg, estado_comanda)
        view_name: Nombre de la vista (para obtener ítems)
    """

    if df is None or df.empty:
        st.info("No hay comandas para mostrar detalles.")
        return

    for idx, row in df.iterrows():
        render_comanda_expander(conn, row, view_name, mode=mode, key_suffix=str(idx))
