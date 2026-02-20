# Análisis técnico del WAC (Weighted Average Cost)

**Fecha de creación:** 2026-02-20  
**Proyecto:** Dashback (Streamlit + MySQL 5.6)  
**Alcance del análisis:** lógica, flujo e interacción con vistas/tablas para el cálculo y consumo de WAC en entorno local (prueba) y entorno remoto (producción).

---

## 1) Resumen ejecutivo

El **WAC (Weighted Average Cost)** en Dashback se resuelve principalmente en la **capa SQL (vistas de base de datos)** y luego se consume desde la app para construir COGS, margen y métricas derivadas.

Punto clave:

- La app **no recalcula WAC crudo** en Python.
- La app consulta vistas ya valorizadas (por ejemplo, `vw_consumo_valorizado_operativa`, `vw_cogs_comanda`, `vw_margen_comanda`).
- El comportamiento funcional entre local y producción es el mismo; cambia la base activa (`mysql` vs `mysql_prod`) y, por tanto, los datos/DDL disponibles.

---

## 2) ¿Qué es WAC y cómo impacta el dashboard?

WAC representa el costo promedio ponderado por insumo. Conceptualmente:

\[
WAC = \frac{\sum (cantidad\_ingresada \times costo\_unitario)}{\sum cantidad\_ingresada}
\]

En el flujo de negocio del dashboard:

1. WAC valoriza el consumo de insumos.
2. Ese consumo valorizado se agrega en COGS por comanda.
3. COGS se cruza con ventas para obtener margen.
4. Sobre esos agregados se derivan KPIs financieros (incluyendo Pour Cost).

Por eso, si WAC está desalineado entre entornos, toda la cadena financiera puede mostrar diferencias.

---

## 3) Flujo end-to-end del WAC (UI → servicios → SQL → vistas)

## 3.1 Capa UI

La sección `Márgenes & Rentabilidad` expone expanders de auditoría que consumen datos donde el WAC ya participa:

- Consumo valorizado (`vw_consumo_valorizado_operativa`)
- COGS por comanda (`vw_cogs_comanda`)
- P&L (`vw_margen_comanda`)

La UI dispara estos bloques bajo demanda (checkboxes), reduciendo carga en producción.

## 3.2 Capa de servicios (Python)

Servicios relevantes:

- `get_consumo_valorizado(...)`
- `get_cogs_por_comanda(...)`
- `get_wac_cogs_summary(...)`
- `get_wac_cogs_detalle(...)`

Estos servicios:

1. Construyen filtros por operativa/fechas (`build_where`).
2. Obtienen SQL desde `query_store.py`.
3. Ejecutan con `fetch_dataframe(...)`.
4. Devuelven DataFrames/listas para render UI.

## 3.3 Capa SQL (fuente real del WAC)

El WAC vive en vistas SQL de backend; la app consume el resultado ya calculado a través de vistas de nivel superior. Cadena funcional esperada:

1. Vistas de WAC por producto (según implementación de BD)
2. Vistas de consumo (cantidades)
3. Vista de consumo valorizado (WAC aplicado)
4. Vista COGS por comanda
5. Vista de margen por comanda

---

## 4) Interacción con vistas y tablas (mapa técnico)

## 4.1 Tablas base involucradas

En términos de dominio, la cadena usa principalmente:

- `alm_ingreso` (histórico de ingresos/costos de inventario)
- `alm_producto` (maestro de productos/insumos)
- `bar_comanda` (cabecera de comandas)
- `bar_detalle_comanda_salida` (detalle vendido/consumido)
- `ope_operacion` (contexto operativo)
- `parameter_table` (catálogos de estados/tipos)

## 4.2 Vistas de costo/consumo y salida financiera

Vistas clave de la cadena WAC/COGS:

- `vw_consumo_insumos_operativa` (consumo sin valorar, control de cantidades)
- `vw_consumo_valorizado_operativa` (consumo valorizado: cantidad + WAC + costo)
- `vw_cogs_comanda` (COGS agregado por comanda)
- `vw_margen_comanda` (ventas + COGS + margen)

Nota de consistencia documental:

- En la documentación aparece nomenclatura WAC como `vw_wac_producto_almacen` y también `vw_wac_global_producto` según contexto histórico.
- La app actual no consulta esas vistas directamente en Python; consume las vistas ya agregadas de consumo/COGS/margen.

---

## 5) Consultas del dashboard que reflejan WAC

## 5.1 Consumo valorizado

La consulta de `q_consumo_valorizado(...)` toma:

- `cantidad_consumida_base`
- `wac_operativa`
- `costo_consumo`

desde `vw_consumo_valorizado_operativa`, y por lo tanto es el punto más directo para auditar cómo se está aplicando WAC por producto.

## 5.2 COGS por comanda

`q_cogs_por_comanda(...)` consume `vw_cogs_comanda`. Aquí ya no se ve el WAC unitario, pero sí su efecto agregado como costo por comanda.

## 5.3 Resumen P&L

`q_wac_cogs_summary(...)` consume `vw_margen_comanda` y devuelve agregados (`total_ventas`, `total_cogs`, `total_margen`, `margen_pct`).

A este nivel, WAC ya está totalmente incorporado en `total_cogs`.

---

## 6) Local (prueba) vs producción (remoto)

## 6.1 Qué cambia

- La conexión seleccionada desde UI:
  - Local → `connections.mysql`
  - Producción → `connections.mysql_prod`
- Base activa subyacente (usualmente `adminerp_copy` vs `adminerp`).
- Posibles diferencias de DDL, datos, índices y sincronización.

## 6.2 Qué no cambia

- Flujo de aplicación (UI → servicios → SQL)
- Funciones Python y SQL parametrizado
- Reglas de filtrado por contexto (`ops` / `dates` / `none`)
- Forma de presentar resultados en UI

Conclusión: si el WAC difiere entre entornos, la causa más probable está en datos/vistas del entorno, no en la lógica Python.

---

## 7) Filtros y contexto que afectan análisis de WAC

El contexto se define con `build_where(...)`:

- `ops`: `id_operacion BETWEEN :op_ini AND :op_fin`
- `dates`: `fecha_emision BETWEEN :dt_ini AND :dt_fin`
- `none`: sin rango explícito

Esto impacta directamente qué subconjunto de consumo/COGS se audita y puede producir diferencias legítimas entre reportes.

---

## 8) Estrategia de auditoría recomendada para WAC

Para validar consistencia local vs producción:

1. Confirmar base activa (`DATABASE()`) y conexión seleccionada.
2. Verificar existencia de vistas críticas (`vw_consumo_valorizado_operativa`, `vw_cogs_comanda`, `vw_margen_comanda`).
3. Comparar para una misma operativa:
   - consumo valorizado por producto,
   - COGS por comanda,
   - resumen P&L.
4. Si hay delta, bajar un nivel:
   - revisar DDL de vistas,
   - revisar insumos de inventario y costos base,
   - validar recetas/unidades de consumo.

Regla práctica:

- Si falla primero `consumo_sin_valorar`, el problema es de cantidades/receta.
- Si `consumo_sin_valorar` cuadra pero `consumo_valorizado` no, el foco es WAC/costo.
- Si valorizado cuadra y falla margen, revisar cruce de ventas en `vw_margen_comanda`.

---

## 9) Riesgos comunes que distorsionan WAC

1. **DDL no alineado entre entornos** (vistas con lógica distinta).
2. **Datos de inventario incompletos** o costos faltantes en ingresos.
3. **Unidades de medida no homologadas** en recetas/insumos.
4. **Diferencias de catálogo o joins** que alteran exclusiones/inclusiones.
5. **Operativa/rango mal seleccionado** al comparar reportes.

---

## 10) Conclusión final

El WAC en Dashback se comporta como una **capacidad de base de datos** consumida por la app mediante vistas derivadas.  
La aplicación aporta:

- parametrización segura,
- filtros de contexto,
- ejecución controlada,
- visualización y diagnóstico.

La confiabilidad del resultado financiero depende de la coherencia de la cadena SQL (WAC → consumo valorizado → COGS → margen) en cada entorno.

Por tanto, para incidentes de WAC entre local y producción, el orden correcto de diagnóstico es:

1. conexión/base activa,
2. DDL y existencia de vistas,
3. datos de inventario/consumo,
4. resultado agregado en margen.
