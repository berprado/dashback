# 🧭 Evolución del proyecto Dashback (Streamlit + MySQL)

Este documento resume la evolución del dashboard **Dashback**, destacando el crecimiento gradual de métricas y visualizaciones, y las optimizaciones/correcciones aplicadas para operar de forma segura tanto con una base local (sincronizada) como con una base remota (producción).

---

## 1) Punto de partida

El proyecto inicia como un dashboard base en Streamlit, con el objetivo de:

- Conectarse a MySQL mediante **Streamlit Connections** (secrets.toml).
- Determinar automáticamente el **contexto operativo** al abrir (tiempo real vs histórico).
- Mostrar KPIs y visualizaciones apoyadas en las vistas `comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`.

---

## 2) Conexión y estructura (base del proyecto)

### Conexión a MySQL con Streamlit Connections

- Se estandarizó la conexión vía `st.connection(..., type="sql")`.
- Se dejó `.streamlit/secrets.toml` fuera del repo (ignorado por `.gitignore`) y se mantuvo un ejemplo versionable.

### Estructura modular

Se consolidó una estructura clara por responsabilidades:

- `app.py`: UI principal y wiring.
- `src/db.py`: obtención de conexión (cacheada) mediante Streamlit Connections.
- `src/query_store.py`: SQL reutilizable y helpers (construcción de filtros/WHERE).
- `src/metrics.py`: capa de servicio para ejecutar consultas y retornar resultados listos para UI.
- `src/ui/*`: layout y componentes visuales.
- `src/startup.py`: determinación de contexto operativo de arranque.

---

## 3) Lógica de arranque (modo tiempo real vs histórico)

Se implementó la lógica de arranque descrita en los documentos de referencia:

- **Tiempo real** si existe operativa activa (`estado_operacion IN (22, 24)`), usando `comandas_v6`.
- **Histórico** si no hay operativa activa, usando `comandas_v6_todas`.

Esto permitió que el dashboard abra con un contexto coherente sin que el usuario tenga que configurarlo manualmente.

---

## 4) Incremento gradual de métricas y visualizaciones

El dashboard evolucionó por etapas, incorporando información útil de forma incremental:

### 4.1 KPIs base

- Total vendido
- Total comandas
- Ítems vendidos
- Ticket promedio

### 4.2 KPIs operativos

- Comandas pendientes
- Comandas no impresas

Además, se incorporó un módulo opcional para ver:

- IDs de comandas pendientes
- IDs de comandas no impresas

con control de carga (checkbox) y límite configurable para evitar consultas costosas.

### 4.3 Gráficos

- Ventas por hora
- Ventas por categoría
- Top productos
- Ventas por usuario

### 4.4 Detalle bajo demanda

Se agregó una tabla de **detalle** (últimas 500 filas) dentro de un expander. Para rendimiento y experiencia de uso:

- El detalle **no se consulta** hasta que el usuario activa “Cargar detalle”.

---

## 5) Cortesías: corrección de cálculo (punto crítico)

Se incorporaron KPIs específicos de cortesías:

- Total cortesías
- Comandas cortesía
- Ítems cortesía

Y se corrigió el cálculo del **monto de cortesía** para reflejar la realidad de negocio:

- En cortesías, `sub_total` puede ser **0**.
- El valor “real invitado” se registra en `cor_subtotal_anterior`.

Por ello, el KPI suma `COALESCE(cor_subtotal_anterior, sub_total, 0)` cuando `tipo_salida = 'CORTESIA'`.

---

## 6) Selección de entorno: Local vs Producción

Se habilitó la capacidad de elegir el origen de datos desde el sidebar:

- **Local** (`connections.mysql`)
- **Producción** (`connections.mysql_prod`)

Esto permite alternar entre la DB local sincronizada (por ejemplo con dbForge) y el servidor remoto, sin cambiar código.

---

## 7) Compatibilidad con distintos esquemas (adminerp_copy vs adminerp)

Se corrigió un punto clave para despliegue:

- En desarrollo local, las vistas viven en `adminerp_copy`.
- En producción, viven en `adminerp`.

Para evitar hardcodear el esquema, las queries y nombres de vista se volvieron **independientes del esquema**, usando tablas/vistas no calificadas (por ejemplo `comandas_v6`) y confiando en que la DB activa viene definida por la URL de conexión.

---

## 8) Healthcheck y diagnósticos

Se fortaleció la validación de conexión con un healthcheck que:

- Confirma DB activa (`DATABASE()`).
- Verifica la existencia de vistas requeridas (`comandas_v6`, `comandas_v6_todas`, `comandas_v6_base`).

También se agregó un modo de depuración controlado:

- Checkbox “Mostrar SQL/params en errores”.
- Si una consulta falla, se muestran el SQL y parámetros, facilitando diagnóstico sin exponer secretos.

---

## 9) Seguridad de configuración

Se sanitizó el archivo `secrets.toml.example` para que sea **seguro de versionar**, usando placeholders y evitando publicar hosts/credenciales.

---

## 10) Estado actual

El dashboard hoy permite:

- Elegir entorno (Local/Producción).
- Determinar modo (Tiempo real / Histórico) y filtrar histórico por:
  - rango de operativas
  - rango de fechas
- Consultar KPIs, KPIs operativos, cortesías, gráficos y detalle bajo demanda.
- Ver IDs de comandas pendientes/no impresas cuando se requiere.

---

## 11) Próximas ideas (no implementadas aún)

Algunas mejoras candidatas para fases posteriores:

- Prefacturación (facturado vs no facturado).
- Exportación de detalle (CSV/Excel) bajo demanda.
- Autenticación/roles (especialmente si se expone públicamente).
- Cache con TTL por bloque para reducir carga en producción.
- Indicadores adicionales: anuladas, procesadas, comparación por turno/hora, etc.

