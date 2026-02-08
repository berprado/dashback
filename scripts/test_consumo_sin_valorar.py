from __future__ import annotations

import sys
sys.path.insert(0, ".")

from src.db import get_connection
from src.query_store import Filters
from src.metrics import get_consumo_sin_valorar

def main() -> None:
    conn = get_connection("mysql")
    filters = Filters(op_ini=1125, op_fin=1125)
    
    print("Consumo sin valorar (operativa 1125, límite 10):")
    df = get_consumo_sin_valorar(conn, "vw_consumo_insumos_operativa", filters, "ops", limit=10)
    
    if df is None or df.empty:
        print("Sin datos")
    else:
        print(f"\nFilas: {len(df)}")
        print(df.to_string(index=False))

if __name__ == "__main__":
    main()
