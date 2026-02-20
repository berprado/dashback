# Dashback

<p align="center">
   <strong>Dashboard operativo en Streamlit conectado a MySQL 5.6</strong>
</p>

<p align="center">
   <a href="https://www.python.org/">
      <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
   </a>
   <a href="https://streamlit.io/">
      <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.52.2-FF4B4B?logo=streamlit&logoColor=white">
   </a>
   <a href="https://www.mysql.com/">
      <img alt="MySQL" src="https://img.shields.io/badge/MySQL-5.6-4479A1?logo=mysql&logoColor=white">
   </a>
   <a href="https://pandas.pydata.org/">
      <img alt="Pandas" src="https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas&logoColor=white">
   </a>
   <a href="https://plotly.com/python/">
      <img alt="Plotly" src="https://img.shields.io/badge/Plotly-6.x-3F4F75?logo=plotly&logoColor=white">
   </a>
   <a href="https://www.sqlalchemy.org/">
      <img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white">
   </a>
</p>

<p align="center">
   <a href="https://github.com/berprado/dashback/blob/main/LICENSE">
      <img alt="Licencia" src="https://img.shields.io/github/license/berprado/dashback?color=blue">
   </a>
   <a href="https://github.com/berprado/dashback/commits/main">
      <img alt="Último commit" src="https://img.shields.io/github/last-commit/berprado/dashback?color=informational">
   </a>
</p>

<p align="center">
   <a href="#-ejecutar">Ejecutar</a>
   · <a href="#-configuración-de-conexión">Configuración</a>
   · <a href="#-inicio-rápido">Inicio rápido</a>
   · <a href="#-documentación">Docs</a>
   · <a href="#-estructura">Estructura</a>
</p>

> Nota: cuando haya dudas, la fuente de verdad es el código en `src/`.

## ✅ Requisitos
- Python 3.10+
- Streamlit 1.52.2

## 🚀 Inicio rápido
1. Instala dependencias:
   - `pip install -r requirements.txt`
2. Configura conexión:
   - `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
3. Ejecuta:
   - `streamlit run app.py`

## 🔌 Configuración de conexión
1. Copia el ejemplo:
   - `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
2. Edita el `url` según tu entorno.

## ▶️ Ejecutar
- `streamlit run app.py`

## 📚 Documentación
- [docs/01-flujo_inicio_dashboard.md](docs/01-flujo_inicio_dashboard.md): lógica de arranque (tiempo real vs histórico) y casos límite.
- [docs/02-guia_dashboard_backstage.md](docs/02-guia_dashboard_backstage.md): guía técnica por etapas + definición de vistas.
- [docs/03-evolucion_y_mejoras.md](docs/03-evolucion_y_mejoras.md): evolución y cambios implementados (fase 1).
- [docs/analisis_wac_cogs_margenes.md](docs/analisis_wac_cogs_margenes.md): análisis completo de WAC/COGS/márgenes + oportunidades de mejora.
- [docs/playbook_performance_mysql56.md](docs/playbook_performance_mysql56.md): playbook de performance para MySQL 5.6.12 (consultas, índices, checks).
- [docs/reporte_indices_aplicados.md](docs/reporte_indices_aplicados.md): ⭐ **reporte de aplicación de índices** (EXPLAIN antes/después en adminerp_copy).
- [docs/reporte_explain_adminerp_copy.md](docs/reporte_explain_adminerp_copy.md): reporte de EXPLAIN baseline (solo lectura).
- [docs/wac_cogs/consultas_cogs_wac.md](docs/wac_cogs/consultas_cogs_wac.md): guía técnica de consultas COGS y WAC (onboarding).
- [docs/wac_cogs/consultas_kpis_actividad_cortesias.md](docs/wac_cogs/consultas_kpis_actividad_cortesias.md): guía técnica de KPIs, actividad y cortesías (onboarding).
- [docs/wac_cogs/playbook_comparativo_wac_cogs_pourcost_local_vs_produccion_2026-02-20.md](docs/wac_cogs/playbook_comparativo_wac_cogs_pourcost_local_vs_produccion_2026-02-20.md): playbook comparativo de diagnóstico (WAC vs COGS vs Pour Cost).
- [docs/wac_cogs/runbook_rapido_wac_cogs_pourcost_2026-02-20.md](docs/wac_cogs/runbook_rapido_wac_cogs_pourcost_2026-02-20.md): runbook rápido operativo (checklist + SQL mínimo).

Scripts:
- [scripts/create_indexes_safe.sql](scripts/create_indexes_safe.sql): script SQL con verificación previa de índices (modo seguro para MySQL 5.6.12).
- [scripts/apply_indexes_and_explain.py](scripts/apply_indexes_and_explain.py): script Python para aplicar índices y ejecutar EXPLAIN antes/después.
- [scripts/audit_wac_cogs_ddl_consistency.sql](scripts/audit_wac_cogs_ddl_consistency.sql): auditoría read-only WAC/COGS/márgenes entre ambientes (usa `ope_operacion.id AS id_operacion` para compatibilidad de esquema).

Capturas:
- [docs/capturas/](docs/capturas/)

## 🧭 Ruta recomendada de lectura (onboarding)
- **Soporte / incidentes (15-20 min):**
   - [docs/wac_cogs/runbook_rapido_wac_cogs_pourcost_2026-02-20.md](docs/wac_cogs/runbook_rapido_wac_cogs_pourcost_2026-02-20.md)
   - [docs/wac_cogs/playbook_comparativo_wac_cogs_pourcost_local_vs_produccion_2026-02-20.md](docs/wac_cogs/playbook_comparativo_wac_cogs_pourcost_local_vs_produccion_2026-02-20.md)
- **BI / auditoría (45-60 min):**
   - [docs/wac_cogs/analisis_wac_local_vs_produccion_2026-02-20.md](docs/wac_cogs/analisis_wac_local_vs_produccion_2026-02-20.md)
   - [docs/wac_cogs/analisis_cogs_local_vs_produccion_2026-02-20.md](docs/wac_cogs/analisis_cogs_local_vs_produccion_2026-02-20.md)
   - [docs/wac_cogs/analisis_pourcost_local_vs_produccion_2026-02-20.md](docs/wac_cogs/analisis_pourcost_local_vs_produccion_2026-02-20.md)
- **Desarrollo (implementación):**
   - [docs/wac_cogs/consultas_cogs_wac.md](docs/wac_cogs/consultas_cogs_wac.md)
   - [docs/02-guia_dashboard_backstage.md](docs/02-guia_dashboard_backstage.md)
   - [docs/analisis_wac_cogs_margenes.md](docs/analisis_wac_cogs_margenes.md)

## 🧭 Estado de implementación
- ✅ Implementado (lo que corre hoy en este repo): conexión por Streamlit Connections, arranque tiempo real/histórico, KPIs/bloques principales, actividad, gráficos y detalle bajo demanda.
- 🟡 Ideas / futuro: prefacturación, export, sparklines, cache TTL, autenticación/roles (ver "Próximas versiones").

## ✨ Funcionalidades actuales
- **Selección de origen de datos** desde el sidebar: Local (`connections.mysql`) o Producción (`connections.mysql_prod`).
- **Modo automático** al iniciar:
   - *Tiempo real* (operativa activa) usando `comandas_v6`.
   - *Histórico* usando `comandas_v6_todas`, con filtros por **rango de operativas** o **rango de fechas**.
- **KPIs**: total vendido, comandas, ítems, ticket promedio.
   - “Ventas” se calcula solo para comandas finalizadas: `tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.
   - Incluye un **diagnóstico opcional** para comparar vs el log de impresión (cuando `estado_impresion` queda `NULL` en `bar_comanda`).
   - Incluye un toggle “Ventas: usar log de impresión” para calcular ventas/gráficos aceptando IMPRESO vía `vw_comanda_ultima_impresion`.
- **Tooltips/ayudas en KPIs**: cada métrica explica qué mide, qué incluye/excluye y el contexto (vista + filtros) para evitar ambigüedades.
- **Formato Bolivia (moneda)**: montos en `Bs 1.100,33` (miles con punto, decimales con coma) y conteos en `1.100`.
- **Actividad (tiempo real / histórico)**: última comanda, minutos desde la última, y ritmo de emisión (mediana entre comandas para últimas 10 y para el rango completo).
- **Cortesías**: total cortesías (usa `cor_subtotal_anterior` cuando aplica), comandas cortesía e ítems cortesía.
- **Márgenes & Rentabilidad (P&L)**: ventas brutas, COGS, margen bruto y margen % desde `vw_margen_comanda`, con el mismo contexto de filtros.
- **Detalle P&L por comanda**: auditoría de ventas/COGS/margen por comanda desde `vw_margen_comanda` (bajo demanda y con límite configurable).
- **Consumo valorizado de insumos**: análisis logístico de cantidades, WAC y costo por producto desde `vw_consumo_valorizado_operativa` (bajo demanda, ordenado por costo DESC).
- **Consumo sin valorar**: sanidad de cantidades (sin WAC/costos) desde `vw_consumo_insumos_operativa` para detectar errores de receta/multiplicación/unidades (bajo demanda, ordenado por cantidad DESC).
- **COGS por comanda**: costo puro por comanda (sin precio de venta) desde `vw_cogs_comanda`, ideal para cortesías y auditoría de consumo (bajo demanda, ordenado por COGS DESC).
- **Estado operativo**: comandas pendientes, anuladas, impresión pendiente y sin estado de impresión, con opción para ver IDs (con límite).
   - `estado_impresion='PENDIENTE'` es temporal (en cola/por procesar).
   - `estado_impresion=NULL` puede significar “aún no procesada/impresa” o “dato faltante”; se interpreta junto con `estado_comanda`.
   - Impresión pendiente: `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`.
   - Sin estado impresión: `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`.
- **Gráficos (2 columnas)**: 
   - **Ventas por hora** (Combo Chart): Barras de **ventas** vs Línea de **comandas**. Visualiza "baches" operativos (0-23h) y pulso de actividad. Opción de línea de promedio.
   - **Ventas por categoría** (Combo Chart o Torta): Barras de **ventas** vs Línea curva de **unidades**. Toggle barras combinadas/torta.
   - **Top productos** (barras horizontales): ranking con categoría/unidades en tooltip. Límite configurable (5-100).
   - **Ventas por usuario** (barras horizontales): ranking con comandas/ítems/ticket promedio en tooltip. Límite configurable (5-100).
   - **Badge de contexto**: muestra filtros aplicados y estado del toggle de impresión.
   - **Exportación**: botón “⬇️ Descargar CSV” en cada gráfico.
- **Detalle** (últimas 500 filas) bajo demanda.
   - Nota: las columnas monetarias del detalle se formatean como texto para asegurar consistencia visual; por eso, si ordenas esas columnas, el orden puede ser **lexicográfico** (texto) en lugar de numérico.
- **Healthcheck**: botón “Probar conexión” valida conexión y existencia de vistas/objetos requeridos (incluye log de impresión).
- **Debug opcional**: checkbox para mostrar SQL/params cuando ocurre un error.

UX:
- **Contorno por sección en métricas**: colores diferenciados para KPIs, diagnóstico de impresión y estado operativo (mejora visual).

## 🔒 Seguridad / Producción
- La app está pensada para operar en **solo lectura** (consultas `SELECT`).
- En producción, usa credenciales **read-only** siempre que sea posible.

## 🧱 Estructura
- `app.py`: entrypoint Streamlit
- `src/db.py`: conexión vía Streamlit Connections (`st.connection`)
- `src/query_store.py`: queries (`Q_...`) + `fetch_dataframe`
- `src/ui/`: layout y componentes UI
- `docs/`: documentos de referencia de negocio

## 🗺️ Próximas versiones (ideas)
- Prefacturación (facturado vs no facturado).
- Exportación de detalle (CSV/Excel) bajo demanda.
- Sparklines/tendencias en KPIs usando `st.metric(..., chart_data=...)`.
- Cache con TTL por bloque (para reducir carga en producción).
- Autenticación/roles si el dashboard se expone fuera de red interna.
- Más KPIs operativos (anuladas, procesadas, comparativos por hora/turno).
