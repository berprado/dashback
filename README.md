# Dashback

Dashboard operativo en **Streamlit** conectado a **MySQL 5.6**.

## Requisitos
- Python 3.10+
- Streamlit 1.52.2

## Configuración de conexión
1. Copia el ejemplo:
   - `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
2. Edita el `url` según tu entorno.

## Ejecutar
- `streamlit run app.py`

## Documentación
- [docs/01-flujo_inicio_dashboard.md](docs/01-flujo_inicio_dashboard.md): lógica de arranque (tiempo real vs histórico) y casos límite.
- [docs/02-guia_dashboard_backstage.md](docs/02-guia_dashboard_backstage.md): guía técnica por etapas + definición de vistas.
- [docs/03-evolucion_y_mejoras.md](docs/03-evolucion_y_mejoras.md): evolución y cambios implementados (fase 1).

## Funcionalidades actuales
- **Selección de origen de datos** desde el sidebar: Local (`connections.mysql`) o Producción (`connections.mysql_prod`).
- **Modo automático** al iniciar:
   - *Tiempo real* (operativa activa) usando `comandas_v6`.
   - *Histórico* usando `comandas_v6_todas`, con filtros por **rango de operativas** o **rango de fechas**.
- **KPIs**: total vendido, comandas, ítems, ticket promedio.
- **Cortesías**: total cortesías (usa `cor_subtotal_anterior` cuando aplica), comandas cortesía e ítems cortesía.
- **Estado operativo**: comandas pendientes y no impresas, con opción para ver IDs (con límite).
- **Gráficos**: ventas por hora, por categoría, top productos, ventas por usuario.
- **Detalle** (últimas 500 filas) bajo demanda.
- **Healthcheck**: botón “Probar conexión” valida conexión y existencia de vistas requeridas.
- **Debug opcional**: checkbox para mostrar SQL/params cuando ocurre un error.

## Seguridad / Producción
- La app está pensada para operar en **solo lectura** (consultas `SELECT`).
- En producción, usa credenciales **read-only** siempre que sea posible.

## Estructura
- `app.py`: entrypoint Streamlit
- `src/db.py`: conexión vía Streamlit Connections (`st.connection`)
- `src/query_store.py`: queries (`Q_...`) + `fetch_dataframe`
- `src/ui/`: layout y componentes UI
- `docs/`: documentos de referencia de negocio

## Próximas versiones (ideas)
- Prefacturación (facturado vs no facturado).
- Exportación de detalle (CSV/Excel) bajo demanda.
- Cache con TTL por bloque (para reducir carga en producción).
- Autenticación/roles si el dashboard se expone fuera de red interna.
- Más KPIs operativos (anuladas, procesadas, comparativos por hora/turno).
