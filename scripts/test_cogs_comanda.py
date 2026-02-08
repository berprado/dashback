"""Script para validar la consulta COGS por comanda."""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.db import get_connection
from src.metrics import get_cogs_por_comanda
from src.query_store import Filters

def main():
    """Test de COGS por comanda con operativa 1125."""
    
    conn = get_connection("mysql")
    
    # Filtro: operativa 1125
    filters = Filters(op_ini=1125, op_fin=1125)
    mode = "ops"
    
    # Ejecutar consulta
    df = get_cogs_por_comanda(
        conn, 
        "vw_cogs_comanda", 
        filters, 
        mode, 
        limit=10
    )
    
    if df is not None and not df.empty:
        print(f"\nFilas: {len(df)}")
        print(df.head(10).to_string())
    else:
        print("Sin datos.")

if __name__ == "__main__":
    main()
