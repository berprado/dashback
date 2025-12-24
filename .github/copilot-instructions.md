# Dashback Copilot Instructions

## 🏗️ Architecture & Data Flow
- **Frontend**: Streamlit-based dashboard.
- **Backend**: MySQL 5.6.12.
- **Data Access**: 
  - `config/database.py`: Connection management using `mysql-connector-python`.
  - `data/queries.py`: SQL query constants (prefixed with `Q_`) and `fetch_dataframe` helper.
- **Visualization**: `components/charts.py` using Plotly Express.

## 🛠️ Critical Workflows
- **Startup Logic**: The app must first determine the "Operativa" context:
  - **Active (Real-time)**: `estado = 'HAB'` AND `estado_operacion IN (22, 24)`. Use `adminerp_copy.comandas_v6`.
  - **Historical**: `estado_operacion = 23`. Use `adminerp_copy.comandas_v6_todas` with filters.
- **Connection**: Use `st.cache_resource` for `get_connection()` to avoid re-connecting on every rerun.

## 📏 Project Conventions
- **Type Hints**: Always use `from __future__ import annotations` and provide type hints for functions.
- **SQL Standards**:
  - Always filter by `estado = 'HAB'` for both `bar_comanda` and `ope_operacion`.
  - Use `parameter_table` for business states:
    - `id_master = 6`: Operativa (22: EN PROCESO, 23: CERRADO, 24: INICIO CIERRE).
    - `id_master = 7`: Comanda (25: PENDIENTE, 26: PROCESADO, 27: ANULADO).
- **Naming**: SQL constants in `data/queries.py` should be uppercase and prefixed with `Q_`.

## 🧩 Integration Patterns
- **Data Fetching**: Use `fetch_dataframe(conn, query, params)` to get results as Pandas DataFrames.
- **Charts**: Return Plotly figures from functions in `components/charts.py` and display them using `st.plotly_chart(fig)`.

## 📂 Key Files
- [app.py](../app.py): Main entry point and UI layout.
- [config/database.py](../config/database.py): DB connection logic.
- [data/queries.py](../data/queries.py): Centralized SQL queries.
- [docs/01-flujo_inicio_dashboard.md](../docs/01-flujo_inicio_dashboard.md): Business logic for app startup.
