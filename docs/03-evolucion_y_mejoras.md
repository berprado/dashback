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

### 4.3 Estado operativo (operación / impresión)

- Comandas pendientes
- Comandas anuladas
- Comandas no impresas (impresión pendiente)

Y bajo demanda (para evitar carga innecesaria):

- IDs de comandas pendientes
- IDs de comandas no impresas
- IDs de comandas anuladas

con control de carga (checkbox) y límite configurable.

Semántica operativa (importante):
- `estado_impresion='PENDIENTE'` es un estado temporal (en cola de impresión/procesamiento).
- `estado_impresion=NULL` suele aparecer cuando la comanda fue anulada y es permanente.
- Por consistencia, el KPI/IDs de “no impresas” cuentan solo `estado_impresion='PENDIENTE'` (no incluye anuladas).

### 4.4 Gráficos

- Ventas por hora
- Ventas por categoría
- Top productos
- Ventas por usuario

Presentación:
- Los gráficos se organizan en 2 filas de 2 columnas para comparación lado a lado.

### 4.5 Actividad (ritmo de emisión)

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
- Verifica la existencia de vistas requeridas (`comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`).

Diagnóstico controlado:

- Checkbox “Mostrar SQL/params en errores”.
- Si una consulta falla, se muestran SQL y parámetros, facilitando diagnóstico sin exponer secretos.

---

## 9) Rendimiento y UX

- Se evitó polling/auto-refresh continuo; se dejó un refresco manual en modo tiempo real.
- Se cargan recursos pesados (detalle e IDs) solo bajo demanda.

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

---

## 12) Próximas ideas (no implementadas aún)

- Prefacturación (facturado vs no facturado).
- Exportación de detalle (CSV/Excel) bajo demanda.
- Sparklines/tendencias en KPIs usando `st.metric(..., chart_data=...)`.
- Cache con TTL por bloque para reducir carga en producción.
- Autenticación/roles si el dashboard se expone fuera de red interna.
- Más KPIs operativos: anuladas, procesadas, comparativos por hora/turno.

