from __future__ import annotations

from src.db import get_connection
from src.query_store import fetch_dataframe

QUERIES = [
    (
        "resumen",
        """
        SELECT
            SUM(total_venta) AS ventas,
            SUM(cogs_comanda) AS cogs,
            SUM(margen_comanda) AS margen
        FROM vw_margen_comanda
        WHERE id_operacion = 1125;
        """,
    ),
    (
        "detalle_comanda",
        """
        SELECT *
        FROM vw_margen_comanda
        WHERE id_operacion = 1125;
        """,
    ),
    (
        "consumo_valorizado",
        """
        SELECT *
        FROM vw_consumo_valorizado_operativa
        WHERE id_operacion = 1125;
        """,
    ),
    (
        "consumo_sin_valorar",
        """
        SELECT *
        FROM vw_consumo_insumos_operativa
        WHERE id_operacion = 1125;
        """,
    ),
    (
        "cogs_por_comanda",
        """
        SELECT *
        FROM vw_cogs_comanda
        WHERE id_operacion = 1125;
        """,
    ),
]


def main() -> None:
    conn = get_connection("mysql")
    for name, sql in QUERIES:
        df = fetch_dataframe(conn, sql, {})
        print(f"--- {name} rows {0 if df is None else len(df)}")
        if df is None or df.empty:
            print("(sin datos)")
        else:
            print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
