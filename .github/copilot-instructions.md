# Instrucciones Copilot — Dashback

## 🧭 Panorama
- **UI**: Streamlit (v1.52.2) en [app.py](../app.py).
- **Datos**: MySQL 5.6.12 (DB `adminerp_copy`) con vistas `comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`.
- **Estructura**: lógica en `src/` (no usar `config/`, `data/`, `components/` — ya no existen).

## 🔌 Conexión a MySQL (Streamlit Connections)
- Configurar `.streamlit/secrets.toml` (o copiar desde `.streamlit/secrets.toml.example`) con:
  - `[connections.mysql]` + `type = "sql"` + `url = "mysql+mysqlconnector://..."`.
- La app obtiene la conexión con `st.connection("mysql", type="sql")` cacheada en [src/db.py](../src/db.py).
- Dependencia clave: `SQLAlchemy` + `mysql-connector-python` (ver `requirements.txt`).

## 🚦 Flujo de arranque (negocio)
- Al iniciar, determinar contexto de **Operativa** (ver [docs/01-flujo_inicio_dashboard.md](../docs/01-flujo_inicio_dashboard.md)):
  - **Tiempo real**: `ope_operacion.estado='HAB'` y `estado_operacion IN (22,24)` ⇒ usar vista `adminerp_copy.comandas_v6`.
  - **Histórico**: `estado_operacion=23` ⇒ usar `adminerp_copy.comandas_v6_todas` aplicando filtros (rango operativas/fechas).
- Los estados y nombres provienen de `parameter_table` (ver [docs/02-guia_dashboard_backstage.md](../docs/02-guia_dashboard_backstage.md)).

## 🧱 Patrones del código
- **Queries**: constantes `Q_...` en [src/query_store.py](../src/query_store.py). Mantener SQL reutilizable ahí.
- **Fetch**: `fetch_dataframe(conn, query, params)` soporta `SQLConnection.query(...)` y también conexiones `mysql.connector`.
- **UI layout**: cabecera y sidebar en [src/ui/layout.py](../src/ui/layout.py).
- **Charts**: funciones Plotly en [src/ui/components.py](../src/ui/components.py) y se renderizan con `st.plotly_chart(fig)`.

## 📏 Convenciones
- Type hints + `from __future__ import annotations` en todos los módulos.
- SQL: filtrar siempre por estado lógico `HAB` en `bar_comanda` y `ope_operacion` (regla de negocio).
- Streamlit: usar `width="stretch"` en `st.dataframe` (evitar `use_container_width`, deprecado).

## 🗂️ Archivos clave
- [app.py](../app.py): entrada y wiring de UI.
- [src/startup.py](../src/startup.py): lugar para centralizar la detección de modo (realtime/historical).

## ▶️ Ejecutar y validar
- Ejecutar app: `streamlit run app.py`.
- Validar conexión (UI): botón **Probar conexión** (sidebar) en [app.py](../app.py) → usa `Q_HEALTHCHECK`.
- Validar conexión (código): `get_connection()` en [src/db.py](../src/db.py) + `fetch_dataframe()` en [src/query_store.py](../src/query_store.py).
- Config local: `.streamlit/secrets.toml` (ya configurado en este repo) y ejemplo en `.streamlit/secrets.toml.example`.
