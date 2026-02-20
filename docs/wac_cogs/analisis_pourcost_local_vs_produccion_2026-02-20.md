# Análisis técnico del cálculo de Pour Cost

**Fecha de creación:** 2026-02-20  
**Proyecto:** Dashback (Streamlit + MySQL 5.6)  
**Alcance del análisis:** lógica, flujo y relación con vistas/tablas en entorno local (prueba) y entorno remoto (producción) para obtener el Pour Cost.

---

## 1) Resumen ejecutivo

El **Pour Cost** en Dashback se obtiene con la misma lógica en ambos entornos (local/prueba y remoto/producción).  
La diferencia entre entornos **no está en el código SQL ni en la fórmula**, sino en la **conexión activa** seleccionada desde la UI:

- Local: `connections.mysql` (normalmente DB `adminerp_copy`)
- Producción: `connections.mysql_prod` (normalmente DB `adminerp`)

El cálculo final se realiza en Python como:

- `pour_cost_pct = (total_cogs / total_ventas) * 100` (si ventas > 0)

La fuente principal para ese cálculo en el dashboard es la vista:

- `vw_margen_comanda`

---

## 2) Flujo end-to-end (de UI a DB)

### 2.1 Selección de entorno en la UI

1. El usuario elige origen de datos en el sidebar (`Local` / `Producción`).
2. Esa elección define `connection_name` (`mysql` o `mysql_prod`).
3. La app abre conexión con `get_connection(connection_name)`.

Resultado: la app ejecuta la misma lógica contra bases distintas según la URL configurada en secrets.

### 2.2 Determinación de contexto operativo

Con la conexión ya seleccionada, la app determina modo inicial:

- **Tiempo real**: usa `comandas_v6` (si hay operativa activa 22/24)
- **Histórico**: usa `comandas_v6_todas` (si no hay operativa activa)

Esto afecta filtros y contexto visual, pero el bloque de márgenes usa su propia fuente financiera (`vw_margen_comanda`) con los mismos filtros de contexto (`ops` o `dates`, y excepcionalmente `none`).

### 2.3 Ejecución del bloque Márgenes & Rentabilidad

1. La UI de márgenes llama a:
   - `get_wac_cogs_summary(conn, "vw_margen_comanda", filters, mode_for_metrics)`
2. El servicio arma filtros con `build_where(...)`.
3. Se genera SQL consolidado con `q_wac_cogs_summary(...)`.
4. Se ejecuta la consulta con `fetch_dataframe(...)`.
5. Con resultados agregados, se calcula el Pour Cost en Python.
6. La UI muestra KPI y estado visual (verde/amarillo/rojo por umbral).

---

## 3) Cálculo exacto del Pour Cost

En la capa de servicios (`metrics.py`), el flujo de cálculo es:

1. Obtener agregados desde SQL:
   - `total_ventas = SUM(total_venta)`
   - `total_cogs = SUM(cogs_comanda)`
   - `total_margen = SUM(margen_comanda)`
   - `margen_pct = SUM(margen_comanda)/SUM(total_venta)*100`
2. Calcular Pour Cost:

\[
Pour\ Cost\% = \frac{total\_cogs}{total\_ventas} \times 100
\]

con guardia de división por cero:

- si `total_ventas <= 0` entonces `pour_cost_pct = 0.0`.

---

## 4) Interacción con vistas y tablas

## 4.1 Vista directa usada por el cálculo

Para el KPI de Pour Cost, la app consulta directamente:

- `vw_margen_comanda`

La query de resumen consolidado usa:

- `SUM(total_venta)`
- `SUM(cogs_comanda)`
- `SUM(margen_comanda)`

## 4.2 Cadena de dependencias de datos (nivel DB)

Aunque el dashboard no recalcula COGS desde cero en Python, depende de que `vw_margen_comanda` esté correctamente construida sobre la cadena WAC/COGS. En términos funcionales:

1. Tablas base (ventas, detalle, inventario, operaciones, catálogos)
2. Vistas intermedias de consumo/WAC
3. `vw_cogs_comanda`
4. `vw_margen_comanda` (ventas + COGS + margen)
5. Dashboard (resumen P&L + Pour Cost)

Esto implica que cualquier diferencia entre local y producción suele originarse en:

- DDL distinto de vistas
- datos distintos
- estado de sincronización distinto
- índices/rendimiento distinto

más que en la fórmula del dashboard.

---

## 5) Diferencias entre Local (prueba) y Producción (remoto)

## 5.1 Qué sí cambia

- **Conexión/DB activa** según secrets (`mysql` vs `mysql_prod`).
- Usualmente el esquema objetivo:
  - local: `adminerp_copy`
  - producción: `adminerp`

## 5.2 Qué no cambia

- Funciones Python (`metrics.py`, `query_store.py`)
- SQL de resumen para P&L
- Fórmula del Pour Cost
- Componente UI que renderiza indicadores

Conclusión: el comportamiento funcional del cálculo es idéntico; cambian los datos de entrada por entorno.

---

## 6) Filtros que impactan el Pour Cost

Los filtros se construyen centralmente con `build_where(...)`:

- modo `ops`: `id_operacion BETWEEN :op_ini AND :op_fin`
- modo `dates`: `fecha_emision BETWEEN :dt_ini AND :dt_fin`
- modo `none`: sin rango explícito

Estos filtros se aplican también al resumen financiero, por lo que el Pour Cost representa siempre el **contexto activo del dashboard**.

---

## 7) Capa de ejecución SQL y parametrización

La ejecución usa `fetch_dataframe(...)` con dos rutas:

1. `st.connection(...).query(...)` (ruta principal Streamlit Connections)
2. fallback `mysql.connector` con conversión de placeholders `:param` → `%(param)s`

Esto permite mantener una única forma de escribir SQL y ejecutar en ambos entornos sin cambiar las consultas.

---

## 8) Presentación en la UI (umbrales de interpretación)

La UI muestra `Pour Cost %` con semáforo por umbral:

- Verde: 30% a 40%
- Amarillo: 25% a <30% o >40% a 45%
- Rojo: fuera de esos rangos

Nota: los umbrales son de interpretación de negocio en UI; no cambian la fórmula de cálculo.

---

## 9) Hallazgo técnico relevante del análisis

Se observó una consideración operativa de cache:

- `_ttl_for_mode(mode)` define TTL 0 solo cuando `mode == "none"`.
- En tiempo real, la app suele setear `mode_for_metrics = "ops"` (operativa actual), lo que activa TTL corto (300) en lugar de 0.

No altera la fórmula del Pour Cost, pero sí puede influir en la inmediatez de refresco percibida en ciertos escenarios.

---

## 10) Conclusión final

El Pour Cost en Dashback está implementado de forma consistente y trazable:

- **Fuente financiera:** `vw_margen_comanda`
- **Agregación:** SQL consolidado (ventas/cogs/margen)
- **Cálculo final:** servicio Python (`COGS / Ventas * 100`)
- **Visualización:** KPI con umbrales en UI
- **Paridad entre entornos:** lógica idéntica, cambia solo la conexión/DB activa

Por lo tanto, ante diferencias entre local y producción en Pour Cost, el primer foco de auditoría debe ser:

1. DB activa seleccionada,
2. consistencia de vistas (`vw_margen_comanda` y dependencias),
3. datos subyacentes por operativa/rango,
4. no la fórmula en aplicación.
