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

## Estado de implementación
- ✅ Implementado (lo que corre hoy en este repo): conexión por Streamlit Connections, arranque tiempo real/histórico, KPIs/bloques principales, actividad, gráficos y detalle bajo demanda.
- 🟡 Ideas / futuro: prefacturación, export, sparklines, cache TTL, autenticación/roles (ver "Próximas versiones").

## Funcionalidades actuales
- **Selección de origen de datos** desde el sidebar: Local (`connections.mysql`) o Producción (`connections.mysql_prod`).
- **Modo automático** al iniciar:
   - *Tiempo real* (operativa activa) usando `comandas_v6`.
   - *Histórico* usando `comandas_v6_todas`, con filtros por **rango de operativas** o **rango de fechas**.
- **KPIs**: total vendido, comandas, ítems, ticket promedio.
- **Formato Bolivia (moneda)**: montos en `Bs 1.100,33` (miles con punto, decimales con coma) y conteos en `1.100`.
- **Actividad (tiempo real / histórico)**: última comanda, minutos desde la última, y ritmo de emisión (mediana entre comandas para últimas 10 y para el rango completo).
- **Cortesías**: total cortesías (usa `cor_subtotal_anterior` cuando aplica), comandas cortesía e ítems cortesía.
- **Estado operativo**: comandas pendientes, anuladas y no impresas, con opción para ver IDs (con límite).
   - `estado_impresion='PENDIENTE'` es temporal (pendiente de procesar/impresión).
   - `estado_impresion=NULL` suele indicar comanda anulada (estado permanente).
- **Gráficos (2 columnas)**: ventas por hora, por categoría, top productos, ventas por usuario.
- **Detalle** (últimas 500 filas) bajo demanda.
   - Nota: las columnas monetarias del detalle se formatean como texto para asegurar consistencia visual; por eso, si ordenas esas columnas, el orden puede ser **lexicográfico** (texto) en lugar de numérico.
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
- Sparklines/tendencias en KPIs usando `st.metric(..., chart_data=...)`.
- Cache con TTL por bloque (para reducir carga en producción).
- Autenticación/roles si el dashboard se expone fuera de red interna.
- Más KPIs operativos (anuladas, procesadas, comparativos por hora/turno).
