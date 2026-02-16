# 🧭 Evolución del proyecto Dashback — Fase 1 (Streamlit 1.52.2 + MySQL 5.6.12)

Este documento consolida la evolución del dashboard **Dashback** durante la fase inicial, destacando el crecimiento gradual de métricas/visualizaciones, y las optimizaciones/correcciones aplicadas para operar de forma segura y consistente tanto en **local** como en **producción**.

Documentos de referencia:
- `docs/01-flujo_inicio_dashboard.md` (lógica de arranque y casos límite)
- `docs/02-guia_dashboard_backstage.md` (guía técnica y definición de vistas)

---

## 1) Punto de partida

El proyecto inicia como un dashboard operativo en Streamlit, con el objetivo de:

- Conectarse a MySQL mediante **Streamlit Connections** (`secrets.toml`).
- Determinar automáticamente el **contexto operativo** al abrir (tiempo real vs histórico).
- Mostrar KPIs y visualizaciones apoyadas en vistas ya preparadas: `comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`.

---

## 2) Conexión y estructura (base del proyecto)

### 2.1 Conexión a MySQL con Streamlit Connections

- Se estandarizó la conexión vía `st.connection(..., type="sql")`.
- Se dejó `.streamlit/secrets.toml` fuera del repo (ignorado por `.gitignore`) y se mantuvo un ejemplo versionable.
- Se priorizó que toda interacción sea **solo lectura** (SELECT) en el flujo normal.

### 2.2 Estructura modular

Se consolidó una estructura clara por responsabilidades:

- `app.py`: UI principal y wiring.
- `src/db.py`: obtención de conexión (cacheada) mediante Streamlit Connections.
- `src/startup.py`: determinación de contexto operativo de arranque.
- `src/query_store.py`: SQL reutilizable (`Q_...` y `q_...`) + helpers (`Filters`, `build_where`, `fetch_dataframe`).
- `src/metrics.py`: capa de servicio para ejecutar consultas y retornar resultados listos para UI.
- `src/ui/*`: layout y componentes visuales.

---

## 3) Lógica de arranque (modo tiempo real vs histórico)

Se implementó la lógica de arranque descrita en los documentos:

- **Tiempo real** si existe operativa activa (`ope_operacion.estado='HAB'` y `estado_operacion IN (22, 24)`), usando `comandas_v6`.
- **Histórico** si no hay operativa activa, usando `comandas_v6_todas`.

Además, se contempló el caso “operativa activa pero sin ventas aún” como estado normal (no error):

- KPIs en cero.
- Mensajes informativos en UI.

---

## 4) Incremento gradual de métricas y visualizaciones

El dashboard evolucionó por etapas, incorporando información útil de forma incremental:

### 4.1 KPIs base

- Total vendido
- Total comandas
- Ítems vendidos
- Ticket promedio

Definición aplicada (fuente de verdad: vista):
- Para evitar incluir comandas no finalizadas, “Ventas” se calcula solo cuando:
	`tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.

Mejora UX aplicada:
- Se unificó el formato de moneda y conteos para Bolivia.
	- Dinero: `Bs 1.100,33`
	- Conteos: `1.100`
	- El formateo se centraliza en `src/ui/formatting.py` para evitar duplicación.

### 4.2 Cortesías (corrección de negocio)

Se incorporaron KPIs de cortesías:

- Total cortesías
- Comandas cortesía
- Ítems cortesía

Corrección crítica: en cortesías el `sub_total` puede ser 0; el valor real “invitado” se registra en `cor_subtotal_anterior`.

Por eso, el KPI de “Total cortesías” suma `COALESCE(cor_subtotal_anterior, sub_total, 0)` cuando `tipo_salida = 'CORTESIA'`.

### 4.3 Márgenes & Rentabilidad (P&L)

Se incorporó el bloque ejecutivo de P&L con fuente en `vw_margen_comanda`:

- Ventas brutas (suma `total_venta`)
- COGS (suma `cogs_comanda`)
- Margen bruto (suma `margen_comanda`)
- Margen % (margen / ventas)
- Pour Cost % (cogs / ventas)

Este bloque respeta el contexto actual (operativas o fechas) y sirve como validación rápida contra `ope_conciliacion`.

Se agregó el **detalle por comanda** bajo demanda (expander), con límite configurable y formateo Bolivia para montos.

Se agregó el **consumo valorizado de insumos** bajo demanda (expander), mostrando:
- `cantidad_consumida_base` (formateado con 4 decimales)
- `wac_operativa` (formato Bolivia)
- `costo_consumo` (formato Bolivia)

Consulta logística para conciliación de inventario, detección de mermas y análisis de costos por producto.

Se agregó el **consumo sin valorar** bajo demanda (expander), mostrando solo `cantidad_consumida_base`.
Esta consulta aísla el problema de cantidades del problema de costos: si algo falla aquí, el error está en receta/multiplicación/unidades, no en WAC o margen.

Se agregó el **COGS por comanda** bajo demanda (expander), mostrando solo `cogs_comanda` (sin precio de venta).
Ideal para cortesías (tienen COGS pero no ventas) y auditoría de consumo puro. Bisagra entre inventario y finanzas.

### Mejoras en gráficos (optimización y UX)

Se refactorizo toda la sección de gráficos para eliminar redundancias y mejorar la experiencia:

1. **Refactorización de código**: Creado helper `render_chart_section()` que reduce ~120 líneas de código duplicado a ~80 (-33%).

2. **Tooltips enriquecidos**: Los 4 gráficos ahora muestran información adicional en hover (comandas, ítems, ticket promedio, unidades, categorías).

3. **Manejo unificado de vacíos**: Consistencia en mensajes cuando no hay datos, distinguiendo tiempo real sin actividad vs filtros sin resultados.

4. **Ventas por hora**: Cambiado de barras a **gráfico de línea** (mejor semántica temporal) con opción de **línea de promedio** horizontal.

5. **Límites configurables**: Agregados controles en sidebar para top productos (5-100) y ventas por usuario (5-100).

6. **Badge de contexto**: Muestra visualmente el filtro aplicado (📋 Op. X, 📅 Fechas, ⏱️ Tiempo real) y estado del toggle de impresión (📦 Log impresión: ON).

7. **Toggle barras/torta**: Ventas por categoría ahora soporta visualización como **pie chart** (muestra porcentajes y proporciones).

8. **Exportación CSV**: Cada gráfico incluye botón **“⬇️ Descargar CSV”** para exportar los datos.

9. **Biblioteca de componentes extendida**: Agregados `line_chart()`, `pie_chart()`, `area_chart()` con formato Bolivia integrado y soporte completo de hover_data.

### 4.4 Estado operativo (operación / impresión)

- Comandas pendientes
- Comandas anuladas
- Impresión pendiente
- Sin estado de impresión

Y bajo demanda (para evitar carga innecesaria):

- IDs de comandas pendientes
- IDs de comandas con impresión pendiente
- IDs de comandas sin estado de impresión
- IDs de comandas anuladas

con control de carga (checkbox) y límite configurable.

Semántica operativa (importante):
- `estado_impresion='PENDIENTE'` es un estado temporal (en cola de impresión/procesamiento).
- `estado_impresion=NULL` puede aparecer antes de imprimirse (pendiente/no procesada) y también cuando la comanda fue anulada.
- Para desambiguar, se interpreta junto con `estado_comanda`.
- Por consistencia, se separa en 2 KPIs/IDs:
	- Impresión pendiente: comandas **no anuladas** con `estado_impresion='PENDIENTE'`.
	- Sin estado de impresión: comandas **no anuladas** con `estado_impresion IS NULL`.

### 4.5 Gráficos

- Ventas por hora
- Ventas por categoría
- Top productos
- Ventas por usuario

Presentación:
- Los gráficos se organizan en 2 filas de 2 columnas para comparación lado a lado.

### 4.6 Actividad (ritmo de emisión)

Se agregó un bloque de “Actividad” basado en `fecha_emision` para medir el pulso operativo:

- Hora de la última comanda (MAX `fecha_emision`).
- Minutos desde la última comanda.
- Ritmo de emisión (mediana de minutos entre comandas consecutivas):
	- últimas 10 comandas
	- operativa/rango completo

Nota: el cálculo es por comanda (`id_comanda`), no por ítem.

Interpretación rápida del “Ritmo” (importante):
- Se usa **mediana** (no promedio) de los minutos entre comandas consecutivas.
- “Últimas 10” mide el pulso reciente; “operativa/rango” mide el pulso global del contexto.
- Si hay menos de 2 comandas válidas en el conjunto, el ritmo se muestra vacío (no hay intervalos).
- Los “intervalos usados” indican cuántas diferencias de tiempo entraron al cálculo.
- “Min desde última” se calcula contra el reloj del servidor donde corre Streamlit; si el servidor tiene zona horaria distinta a MySQL, ese valor puede diferir de la expectativa.

### 4.6 Detalle bajo demanda

Se agregó una tabla de **detalle** (últimas 500 filas) dentro de un expander.

Optimización: el detalle no se consulta hasta que el usuario activa “Cargar detalle”.

Nota de formato/importante:
- En el detalle, las columnas monetarias se muestran ya formateadas como texto (`Bs ...`) para asegurar consistencia visual.
- Por ese motivo, al ordenar por esas columnas desde la UI, el ordenamiento puede ser **lexicográfico** (texto) y no numérico.

---

## 5) Documentación técnica añadida

Se incorporaron documentos de referencia para consolidar y operar mejor el stack financiero y su performance:

- [docs/analisis_wac_cogs_margenes.md](docs/analisis_wac_cogs_margenes.md): análisis completo de WAC/COGS/márgenes, inconsistencias detectadas y oportunidades de mejora.
- [docs/playbook_performance_mysql56.md](docs/playbook_performance_mysql56.md): playbook de performance para MySQL 5.6.12 con consultas EXPLAIN, checklist de índices y criterios de validación.
- [docs/reporte_explain_adminerp_copy.md](docs/reporte_explain_adminerp_copy.md): reporte de EXPLAIN en adminerp_copy (solo lectura).

Auditorías realizadas (solo lectura):
- DDL de vistas financieras en `adminerp_copy` (WAC/COGS/márgenes).
- Revisión de índices actuales vs checklist mínimo (documentado en el análisis y playbook).

---

## 5) Selección de entorno: Local vs Producción

Se habilitó elegir el origen de datos desde el sidebar:

- **Local** (`connections.mysql`)
- **Producción** (`connections.mysql_prod`)

Esto permite alternar entre la DB local sincronizada (por ejemplo con dbForge) y el servidor remoto, sin cambiar código.

---

## 6) Compatibilidad con distintos esquemas (adminerp_copy vs adminerp)

Se corrigió un punto clave para despliegue:

- En desarrollo local, las vistas viven en `adminerp_copy`.
- En producción, viven en `adminerp`.

Para evitar hardcodear el esquema:

- Las queries y vistas se volvieron independientes del esquema usando nombres no calificados (ej. `comandas_v6`).
- La DB activa se determina por el `DATABASE()` definido en la URL de conexión.

---

## 7) Compatibilidad técnica: placeholders SQL y Streamlit

Se estandarizó el uso de placeholders estilo SQLAlchemy (`:param`) para funcionar correctamente con Streamlit Connections.

Cuando aplica (ruta alternativa con `mysql.connector`), se convierte a `%(param)s`.

También se actualizó la UI para usar `width="stretch"` en tablas/gráficos en lugar de opciones deprecadas.

---

## 8) Healthcheck y diagnósticos

Se fortaleció la validación de conexión con un healthcheck que:

- Confirma la DB activa (`DATABASE()`).
- Verifica la existencia de vistas/tablas requeridas (`comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`, `comandas_v7`, `vw_comanda_ultima_impresion`, `bar_comanda_impresion`).

Diagnóstico controlado:

- Checkbox “Mostrar SQL/params en errores”.
- Si una consulta falla, se muestran SQL y parámetros, facilitando diagnóstico sin exponer secretos.

### 8.1 Diagnóstico de impresión (impacto en ventas)

Se observó un caso operativo relevante:

- `bar_comanda.estado_impresion` puede quedar `NULL` aunque la impresión física ya ocurrió.
- `comandas_v6` refleja fielmente `bar_comanda` (por eso mantiene el `NULL`).
- El log (`bar_comanda_impresion` / `vw_comanda_ultima_impresion`) puede ya contener `IMPRESO`.
- `comandas_v7` toma su estado de impresión desde `vw_comanda_ultima_impresion`.

Para evitar diagnósticos “a ciegas” cuando el KPI de ventas queda subestimado por el `NULL`, se agregó en la UI:

- Un expander de diagnóstico que calcula “Total vendido (con log)” y el delta contra el cálculo estricto.
- Un toggle “Ventas: usar log de impresión” para aplicar la señal del log también a KPIs y gráficos.

---

## 9) Rendimiento y UX

- Se evitó polling/auto-refresh continuo; se dejó un refresco manual en modo tiempo real.
- Se cargan recursos pesados (detalle e IDs) solo bajo demanda.
- Se incorporó cache por modo (realtime sin cache, histórico con cache corto).
- Se agregó fallback por sesión en gráficos para degradación graceful si falla la BD.
- Se aplicó `@st.fragment` en KPIs, márgenes, gráficos y detalle para reducir reruns completos.
- Se configuró theming avanzado (Google Fonts, Material Symbols y paleta de charts).

Mejora visual:
- Se añadieron contornos con colores diferenciados por grupo de métricas (KPIs / diagnóstico de impresión / estado operativo) para mejorar lectura rápida.

### 9.1 Estándar de ayudas (tooltips `help`)

Se estandarizaron las ayudas (`help=`) en KPIs y métricas para reducir interpretaciones incorrectas.

Principios aplicados:
- Cada métrica aclara **qué mide**, **qué incluye/excluye** y **en qué contexto** se calcula (vista + filtros activos).
- Se diferencia explícitamente entre:
	- **Ventas finalizadas** (VENTA/PROCESADO/IMPRESO) para KPIs/gráficos de ventas.
	- **Actividad** basada en `fecha_emision` (pulso operativo), sin filtrar por tipo/estado.
	- **Estado operativo** (pendientes/anuladas/impresión pendiente/sin estado) usando semántica de impresión consistente.

---

## 10) Seguridad de configuración

- Se sanitizó `secrets.toml.example` para que sea seguro de versionar (placeholders y sin hosts/credenciales reales).
- Recomendación operativa: credenciales de producción **solo lectura**.

---

## 11) Estado actual

El dashboard hoy permite:

- Elegir entorno (Local/Producción).
- Determinar modo (Tiempo real / Histórico) y filtrar histórico por rango de operativas o por fechas.
- Consultar KPIs, cortesías, estado operativo, gráficos y detalle bajo demanda.
- Consultar actividad (última comanda / minutos desde última / ritmo de emisión).
- Validar conexión y vistas desde el healthcheck.
- `app.py` modularizado en `src/ui/sections/` para aislar secciones de UI.
- Conexión cacheada por sesión (`scope="session"`) con `on_release` y validación opcional.
- JOIN de impresión centralizado en helper para evitar duplicación.
- Healthcheck extendido con vistas P&L.

Actualización (documentación):
- Se ajustó docs/02 para alinear explícitamente qué está implementado hoy (Filters/build_where) y aclarar que el toggle de impresión usa el log (`vw_comanda_ultima_impresion`) vía joins (no consume `comandas_v7`).
- Pasada editorial en docs/02 y README: separar mejor “Implementado” vs “Referencia/Futuro” y eliminar snippets que no coincidían con el código real.

Actualización (repo / calidad):
- Se agregó `.gitattributes` para normalizar finales de línea (LF) en archivos de código y documentación, evitando warnings LF/CRLF en Windows.

---

## 12) Mejoras en Visualizaciones (Gráficos Combinados)

Se evolucionó la estrategia de graficado para mejorar la densidad de información sin perder claridad:

### 12.1 Estrategia "Combo Chart"
Se implementó composición de gráficos (Barras + Líneas) con doble eje Y usando `plotly.subplots`:

- **Ventas por Hora**:
  - **Barras**: Monto vendido (Bs).
  - **Línea**: Cantidad de Comandas (#).
  - **Mejora de datos**: Se normalizó el eje temporal (0-23h) rellenando con ceros los huecos sin ventas. Esto permite visualizar correctamente los "baches" operativos que antes quedaban ocultos por la interpolación lineal.

- **Ventas por Categoría**:
  - **Barras**: Monto vendido (Bs).
  - **Línea**: Cantidad de Unidades (Shape *spline* para suavidad visual).
  - Permite correlacionar categorías de volumen (muchas unidades, ticket bajo) vs valor (pocas unidades, ticket alto).

**Beneficio**: El usuario obtiene contexto operativo (pulso de comandas / volumen de unidades) en el mismo espacio visual, facilitando decisiones rápidas.

---

## 13) Análisis de Performance y Aplicación de Índices (MySQL 5.6.12)

### 13.1 Auditoría de Vistas y Diagnóstico

**Objetivo:** Identificar cuellos de botella en las consultas de WAC/COGS/márgenes para operativas activas y rangos de fechas.

**Proceso:**
1. Se auditó la estructura DDL real de las vistas financieras en `adminerp_copy` (entorno de pruebas).
2. Se ejecutó `SHOW INDEX` en todas las tablas base para identificar índices existentes.
3. Se identificaron gaps críticos:
   - `bar_comanda`: faltaban índices compuestos para filtros de estado y operación+fecha.
   - `bar_detalle_comanda_salida`: faltaba índice compuesto para joins de comanda+producto.
   - `alm_producto`, `ope_operacion`, `parameter_table`: faltaban índices simples para filtros comunes.

**Hallazgos clave:**
- Columna real es `fecha` (no `fecha_emision`) en `bar_comanda`.
- `alm_ingreso` no tiene `id_producto` (está en `alm_detalle_ingreso`).
- Vistas WAC/COGS consumen `vw_wac_producto_almacen` (no `vw_wac_global_producto`).

📄 **Documentación:** `docs/analisis_wac_cogs_margenes.md` (secciones 7.7 y 7.8)

### 13.2 Índices Recomendados y Aplicados

Se crearon **6 índices** en el entorno de pruebas (`adminerp_copy`):

**Críticos (MUST):**
1. `bar_comanda.idx_bar_comanda_op_fecha` → `(id_operacion, fecha)`
2. `bar_comanda.idx_bar_comanda_estados` → `(estado, estado_comanda, estado_impresion)`
3. `bar_detalle_comanda_salida.idx_detalle_comanda_producto` → `(id_comanda, id_producto)`

**Opcionales (SHOULD):**
4. `alm_producto.idx_alm_producto_estado` → `(estado)`
5. `ope_operacion.idx_ope_operacion_estado` → `(estado, estado_operacion)`
6. `parameter_table.idx_parameter_master_estado` → `(id_master, estado)`

📜 **Scripts:**
- `scripts/create_indexes_safe.sql` (con verificación previa vía `information_schema`)
- `scripts/apply_indexes_and_explain.py` (aplicación automatizada + EXPLAIN antes/después)

### 13.3 Resultados: EXPLAIN Antes/Después

| Consulta | Tipo (antes → después) | Rows (antes → después) | Mejora |
|----------|------------------------|------------------------|--------|
| **Q4_comandas_states_filter** | ALL → ref | 56,934 → 1 | ✅ **100%** |
| Q2_consumo_valorizado | ref → ref | 356 → 284 | ✅ 20.2% |
| Q1_margen_por_operacion | ref → ref | 10 → 10 | → Sin cambio visible |
| Q3_comandas_ventas_activas | ref → ref | 148 → 148 | → Sin cambio |

**Mejora destacada:**
- **Q4** (filtros de estado): cambió de `type=ALL` (full table scan de 56,934 rows) a `type=ref` (index lookup con 1 row estimado). El índice `idx_bar_comanda_estados` es ahora un **covering index** (Using index) → no necesita acceder a la tabla.

**Limitaciones observadas:**
- "Using temporary; Using filesort" persiste en vistas anidadas (limitación de MySQL 5.6.12, no de índices).
- Consultas simples que ya tenían índice en FK no muestran mejora visible.

📊 **Reporte completo:** `docs/reporte_indices_aplicados.md`  
📦 **Datos crudos (JSON):** `docs/explain_before_after_report.json`

### 13.4 Siguientes Pasos

- **Producción:** Aplicar índices críticos (MUST) en horario de baja carga.
- **Monitoreo:** Validar tiempo de respuesta de `get_margen_comanda()` y `get_comandas_by_filter()` (objetivo: <1.5s).
- **Testing:** Verificar que el dashboard carga correctamente en realtime y histórico después de aplicar índices.

📘 **Playbook de performance:** `docs/playbook_performance_mysql56.md`

### 13.5 Aclaraciones sobre DDL (Febrero 2026)

Durante la auditoría de DDL real en `adminerp_copy` se identificaron diferencias entre tabla base y vistas:

**Columnas de fecha:**
- **Tabla base:** `bar_comanda.fecha` (datetime)
- **Vistas dashboard:** `comandas_v6.fecha_emision` (renombrada desde `bar_comanda.fecha`)
- **Implicación:** Los índices se crean sobre `fecha` en la tabla base, pero el código consulta `fecha_emision` en las vistas. Esto es correcto y no requiere cambios.

**Columna id_producto en almacén:**
- **`alm_ingreso`:** NO tiene columna `id_producto`
- **`alm_detalle_ingreso`:** SÍ tiene `id_producto` (detalle de cada ingreso)
- **Implicación:** El WAC se calcula desde el join `alm_ingreso` ↔ `alm_detalle_ingreso`. Índices relevantes deben estar en `alm_detalle_ingreso`.

**Vistas WAC:**
- **Usada actualmente:** `vw_wac_producto_almacen` (calcula WAC desde ingresos históricos con `id_almacen=1`)
- **Existe pero no se usa:** `vw_wac_global_producto` (toma WAC desde `vw_costo_heredado_producto`)
- **Implicación:** El sistema usa WAC global calculado desde ingresos históricos, no WAC por almacén variable.

Documentación actualizada: `docs/playbook_performance_mysql56.md`, `docs/analisis_wac_cogs_margenes.md`, `scripts/create_indexes_safe.sql`, `docs/reporte_indices_aplicados.md`.

---

## 14) Próximas ideas (no implementadas aún)

- Prefacturación (facturado vs no facturado).
- Exportación de detalle (CSV/Excel) bajo demanda.
- Sparklines/tendencias en KPIs usando `st.metric(..., chart_data=...)`.
- Cache con TTL por bloque para reducir carga en producción.
- Autenticación/roles si el dashboard se expone fuera de red interna.
- Más KPIs operativos: anuladas, procesadas, comparativos por hora/turno.
- Auto-refresh controlado (toggle + intervalo).
- Pool/DSN tuning (pool_size, pool_recycle, timeouts).

