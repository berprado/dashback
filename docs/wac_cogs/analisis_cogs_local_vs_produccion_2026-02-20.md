# Análisis técnico del COGS (Cost of Goods Sold)

**Fecha de creación:** 2026-02-20  
**Proyecto:** Dashback (Streamlit + MySQL 5.6)  
**Alcance del análisis:** lógica, flujo e interacción con vistas/tablas para obtener COGS en entorno local (prueba) y entorno remoto (producción).

---

## 1) Resumen ejecutivo

El **COGS** en Dashback se obtiene principalmente desde vistas SQL de negocio y se consume en la app para auditoría y KPIs financieros.

Puntos clave:

- La app no construye COGS desde cero en Python; **consulta vistas ya calculadas**.
- La vista más directa para costo por comanda es `vw_cogs_comanda`.
- El COGS total usado en P&L proviene de `vw_margen_comanda` (`SUM(cogs_comanda)`).
- Local y producción usan la misma lógica de aplicación; cambia la conexión/base activa.

---

## 2) Definición funcional de COGS en este dashboard

En este contexto, COGS representa el **costo de insumos consumidos** asociado a las comandas.

A nivel agregado en el dashboard:

\[
COGS_{total} = \sum cogs\_comanda
\]

A nivel operativo, COGS resulta de:

1. cantidades consumidas,
2. valorización por WAC,
3. agregación por comanda.

---

## 3) Flujo end-to-end (UI → servicios → SQL → DB)

## 3.1 Capa UI

En la sección `Márgenes & Rentabilidad`, la UI tiene expanders que consumen COGS en distintos niveles:

- **COGS por comanda** (vista directa de costo): `vw_cogs_comanda`
- **P&L consolidado** (incluye COGS total): `vw_margen_comanda`
- **Consumo valorizado** (explica de dónde viene el costo): `vw_consumo_valorizado_operativa`

La carga es bajo demanda (checkbox), lo cual reduce impacto de consultas pesadas.

## 3.2 Capa de servicios (Python)

Servicios relacionados:

- `get_cogs_por_comanda(...)`
- `get_wac_cogs_summary(...)`
- `get_wac_cogs_detalle(...)`
- `get_consumo_valorizado(...)`
- `get_consumo_sin_valorar(...)`

Responsabilidades:

1. aplicar filtros por contexto (`build_where`),
2. generar SQL desde `query_store.py`,
3. ejecutar con `fetch_dataframe`,
4. retornar resultados para render.

## 3.3 Capa SQL (fuente de verdad)

Consultas principales:

- `q_cogs_por_comanda(view_name, where_sql, limit)`
- `q_wac_cogs_summary(view_name, where_sql)`
- `q_wac_cogs_detalle(view_name, where_sql, limit)`

Vista fuente por caso:

- costo puro por comanda: `vw_cogs_comanda`
- resumen financiero (incluye COGS): `vw_margen_comanda`

---

## 4) Interacción con vistas y tablas

## 4.1 Tablas base (origen del costo)

La cadena de costo se alimenta, en términos de dominio, de tablas como:

- `bar_comanda`
- `bar_detalle_comanda_salida`
- `alm_ingreso`
- `alm_producto`
- `ope_operacion`
- `parameter_table`

## 4.2 Vistas intermedias y finales

Cadena funcional esperada:

1. consumo sin valorar (`vw_consumo_insumos_operativa`)
2. consumo valorizado (`vw_consumo_valorizado_operativa`)
3. COGS por comanda (`vw_cogs_comanda`)
4. margen por comanda (`vw_margen_comanda`)

Interpretación:

- `vw_consumo_insumos_operativa` valida cantidades.
- `vw_consumo_valorizado_operativa` aplica costo unitario (WAC).
- `vw_cogs_comanda` agrega costo por comanda.
- `vw_margen_comanda` cruza ese costo con ventas.

---

## 5) Cómo se usa COGS en los bloques del dashboard

## 5.1 COGS por comanda (auditoría de costo puro)

La app consulta `vw_cogs_comanda` para listar:

- `id_operacion`
- `id_comanda`
- `cogs_comanda`
- contexto operativo (mesa/usuario/estado vía join a `bar_comanda` en query de detalle)

Uso típico:

- auditoría de comandas costosas,
- análisis de cortesías (pueden tener COGS sin venta),
- investigación de outliers.

## 5.2 Resumen ejecutivo P&L

En `vw_margen_comanda`, el dashboard agrega:

- `SUM(total_venta)`
- `SUM(cogs_comanda)`
- `SUM(margen_comanda)`

De aquí sale el COGS total visible en KPI de Márgenes.

## 5.3 Relación con Pour Cost y Margen

Una vez consolidado COGS:

- `Pour Cost % = (COGS / Ventas) × 100`
- `Margen %` se deriva de margen/ventas

Por eso, cualquier sesgo en COGS se refleja inmediatamente en esos indicadores.

---

## 6) Local (prueba) vs producción (remoto)

## 6.1 Qué cambia

- conexión seleccionada en UI:
  - Local: `connections.mysql`
  - Producción: `connections.mysql_prod`
- base activa subyacente (habitualmente `adminerp_copy` vs `adminerp`)
- posibles diferencias de DDL, datos e índices

## 6.2 Qué no cambia

- funciones de la app,
- SQL parametrizado,
- reglas de filtrado,
- visualización en UI.

Conclusión: las diferencias de COGS entre entornos suelen ser de **datos/estructura DB**, no de lógica Python.

---

## 7) Filtros y contexto que afectan el COGS

El filtrado es centralizado en `build_where`:

- `ops`: por rango de `id_operacion`
- `dates`: por rango de `fecha_emision`
- `none`: sin filtro explícito

Este contexto se aplica a las consultas de costo y define exactamente qué universo se está comparando.

---

## 8) Estrategia de diagnóstico recomendada para COGS

Orden sugerido para investigar discrepancias:

1. Validar conexión y DB activa (`DATABASE()`).
2. Confirmar existencia de vistas críticas (`vw_cogs_comanda`, `vw_margen_comanda`, `vw_consumo_valorizado_operativa`, `vw_consumo_insumos_operativa`).
3. Comparar misma operativa/rango en ambos entornos:
   - consumo sin valorar,
   - consumo valorizado,
   - COGS por comanda,
   - COGS total en P&L.
4. Si hay delta, revisar DDL real y datos base de inventario/recetas.

Regla práctica:

- Si no cuadra `consumo_sin_valorar`, problema de cantidades/receta.
- Si cuadra sin valorar pero no valorizado, problema de costo/WAC.
- Si valorizado cuadra y margen no, revisar cruce de ventas en `vw_margen_comanda`.

---

## 9) Riesgos típicos que alteran el COGS

1. Vistas no alineadas entre local y producción.
2. Costos de inventario incompletos o desactualizados.
3. Errores de unidad de medida (receta vs inventario).
4. Cambios de lógica en vistas no auditados en ambos ambientes.
5. Comparaciones hechas con operativas/rangos distintos.

---

## 10) Conclusión final

En Dashback, COGS es una métrica de cadena SQL (consumo → valorización → agregación) que la app consume y presenta con contexto operativo.

La app garantiza:

- ejecución parametrizada,
- filtros consistentes,
- trazabilidad por bloque (consumo, COGS, margen),
- visualización de auditoría bajo demanda.

Ante discrepancias de COGS entre local y producción, el diagnóstico debe centrarse primero en la base activa, la consistencia de vistas y datos de origen, antes de cuestionar la lógica del dashboard.
