# Playbook comparativo de diagnóstico: WAC vs COGS vs Pour Cost

**Fecha de creación:** 2026-02-20  
**Proyecto:** Dashback (Streamlit + MySQL 5.6)  
**Objetivo:** disponer de una matriz única, práctica y accionable para diagnosticar diferencias entre entorno local (prueba) y remoto (producción) en WAC, COGS y Pour Cost.

---

## 1) Resumen ejecutivo

Este playbook unifica los tres niveles de análisis financiero:

1. **WAC** (costo unitario promedio ponderado),
2. **COGS** (costo total de lo vendido por comanda/operativa),
3. **Pour Cost** (ratio COGS/Ventas).

Relación jerárquica:

\[
WAC \rightarrow COGS \rightarrow Pour\ Cost
\]

Si hay desviación en Pour Cost, la causa raíz suele estar aguas arriba (COGS o WAC).

---

## 2) Alcance de entorno (local vs producción)

En la app, la lógica es la misma para ambos entornos; cambia la conexión seleccionada:

- Local: `connections.mysql` (usualmente DB `adminerp_copy`)
- Producción: `connections.mysql_prod` (usualmente DB `adminerp`)

Por diseño, las consultas usan nombres no calificados (`vw_margen_comanda`, etc.), por lo que la DB activa la define la URL de conexión.

---

## 3) Mapa de capas (de dónde sale cada métrica)

## 3.1 Capa base (datos fuente)

- `alm_ingreso`, `alm_producto` (costos de inventario)
- `bar_comanda`, `bar_detalle_comanda_salida` (ventas y detalle)
- `ope_operacion` (contexto operativo)
- `parameter_table` (catálogos/estados)

## 3.2 Capa de transformación (vistas SQL)

- `vw_consumo_insumos_operativa` (cantidades)
- `vw_consumo_valorizado_operativa` (cantidades + WAC + costo)
- `vw_cogs_comanda` (costo por comanda)
- `vw_margen_comanda` (ventas + COGS + margen)

## 3.3 Capa app (servicios y UI)

- `metrics.py`: servicios de consulta y agregación de resultados
- `query_store.py`: SQL parametrizado
- `src/ui/sections/margenes.py`: render y auditoría en UI

---

## 4) Matriz comparativa (WAC vs COGS vs Pour Cost)

| Dimensión | WAC | COGS | Pour Cost |
|---|---|---|---|
| **Qué mide** | Costo unitario promedio de insumo | Costo total de insumos consumidos | Proporción costo/venta |
| **Fórmula conceptual** | $\sum(q\*c)/\sum(q)$ | $\sum cogs\_comanda$ | $(COGS/Ventas)\times100$ |
| **Granularidad típica** | Producto/insumo | Comanda / operativa | Operativa / rango |
| **Dónde se calcula principalmente** | Vistas SQL de costo | Vistas SQL de costo agregado | Servicio Python sobre agregados SQL |
| **Vista clave en app** | `vw_consumo_valorizado_operativa` (exposición de WAC aplicado) | `vw_cogs_comanda` y `vw_margen_comanda` | `vw_margen_comanda` + cálculo `metrics.py` |
| **Uso en UI** | Auditoría de valorización | Auditoría de costo puro + KPI COGS | KPI semaforizado (verde/amarillo/rojo) |
| **Impacto de errores** | Distorsiona todo lo aguas abajo | Distorsiona margen y pour cost | Distorsiona lectura ejecutiva |
| **Dónde depurar primero** | costos inventario + DDL de vistas WAC | consumo valorizado + agregación por comanda | validar COGS y ventas agregadas |

---

## 5) Matriz de síntomas y causa raíz probable

| Síntoma observado | WAC | COGS | Pour Cost | Causa raíz probable |
|---|---:|---:|---:|---|
| `consumo_sin_valorar` no cuadra entre entornos | ⚪ | 🔴 | 🔴 | Diferencia en receta/unidades/cantidades, no en WAC |
| `consumo_sin_valorar` cuadra pero `consumo_valorizado` no | 🔴 | 🔴 | 🔴 | WAC/costos de inventario distintos |
| `cogs_comanda` difiere pero valorizado coincide | ⚪/🟡 | 🔴 | 🔴 | Agregación o DDL de `vw_cogs_comanda` distinta |
| COGS total coincide pero Pour Cost difiere | ⚪ | ⚪ | 🔴 | Diferencia en ventas (`vw_margen_comanda`) o filtros aplicados |
| Todo coincide local, difiere solo prod | 🟡 | 🟡 | 🟡 | Entorno remoto con datos no sincronizados / DDL distinto |
| Diferencias solo en rango de fechas | 🟡 | 🟡 | 🟡 | Contexto/filtro diferente (`ops` vs `dates` / timezone / rango) |

Leyenda: 🔴 alta incidencia, 🟡 posible incidencia, ⚪ baja incidencia directa.

---

## 6) Flujo único de diagnóstico (paso a paso)

### Paso 1 — Asegurar comparabilidad

1. Verifica conexión seleccionada (local/producción).
2. Verifica base activa (`DATABASE()`).
3. Usa misma operativa o mismo rango en ambos entornos.
4. Confirma mismo criterio de filtro (`ops` o `dates`).

### Paso 2 — Validar estructura mínima

Confirmar existencia de vistas críticas:

- `vw_consumo_insumos_operativa`
- `vw_consumo_valorizado_operativa`
- `vw_cogs_comanda`
- `vw_margen_comanda`

### Paso 3 — Diagnóstico por capas

1. **Cantidades**: comparar consumo sin valorar.
2. **Valorización**: comparar consumo valorizado (incluyendo WAC aplicado).
3. **Costo agregado**: comparar COGS por comanda.
4. **Resultado ejecutivo**: comparar COGS total, margen y Pour Cost.

### Paso 4 — Aislar desviación

Cuando encuentres la primera capa que diverge, detén la escalada y enfoca análisis ahí.  
No tiene sentido depurar Pour Cost si la diferencia ya nació en consumo/costo.

---

## 7) Checklist operativo rápido (15 minutos)

- [ ] Misma conexión lógica y DB activa confirmada.
- [ ] Misma operativa/rango en ambos entornos.
- [ ] Vistas requeridas existen en ambos entornos.
- [ ] `consumo_sin_valorar` comparable.
- [ ] `consumo_valorizado` comparable.
- [ ] `cogs_comanda` comparable.
- [ ] `vw_margen_comanda` comparable.
- [ ] Pour Cost calculado sobre mismos agregados.

Si uno falla, ese es el punto de entrada del RCA (root cause analysis).

---

## 8) Tabla de decisiones (qué hacer según dónde falle)

| Primer punto que falla | Acción inmediata | Dueño sugerido |
|---|---|---|
| Consumo sin valorar | Auditar receta, factores de conversión, unidades | Operaciones + Datos |
| Consumo valorizado | Auditar costos base e implementación WAC | Inventario + BI/DBA |
| COGS por comanda | Auditar lógica de agregación y DDL de vista | BI/DBA |
| Margen/Pour Cost | Auditar cruce con ventas y filtros de contexto | BI + Producto |
| Solo producción falla | Revisar sincronización de datos/DDL/índices prod | DBA + Infra |

---

## 9) Riesgos transversales y controles preventivos

### 9.1 Riesgos frecuentes

1. DDL de vistas no alineado entre ambientes.
2. Diferencias de datos maestros/costos de inventario.
3. Cambios en recetas no replicados.
4. Comparaciones con filtros diferentes.
5. Interpretación de resultados sin validar base activa.

### 9.2 Controles recomendados

1. Auditoría periódica de DDL entre `adminerp_copy` y `adminerp`.
2. Script de validación de vistas críticas previo a despliegue.
3. Comparativo automatizado por operativa de control (golden set).
4. Checklist obligatorio de contexto antes de reportar discrepancias.

---

## 10) Consultas tipo (plantilla de verificación)

> Ajustar según esquema y vistas disponibles en cada entorno.

### 10.1 P&L consolidado (base para COGS y Pour Cost)

```sql
SELECT
    COALESCE(SUM(total_venta), 0) AS total_ventas,
    COALESCE(SUM(cogs_comanda), 0) AS total_cogs,
    COALESCE(SUM(margen_comanda), 0) AS total_margen,
    ROUND(
        COALESCE(SUM(cogs_comanda), 0) / NULLIF(COALESCE(SUM(total_venta), 0), 0) * 100,
        2
    ) AS pour_cost_pct
FROM vw_margen_comanda
WHERE id_operacion BETWEEN :op_ini AND :op_fin;
```

### 10.2 COGS por comanda (top impacto)

```sql
SELECT
    id_operacion,
    id_comanda,
    cogs_comanda
FROM vw_cogs_comanda
WHERE id_operacion BETWEEN :op_ini AND :op_fin
ORDER BY cogs_comanda DESC
LIMIT 100;
```

### 10.3 Consumo valorizado (auditoría de WAC aplicado)

```sql
SELECT
    id_operacion,
    id_producto,
    cantidad_consumida_base,
    wac_operativa,
    costo_consumo
FROM vw_consumo_valorizado_operativa
WHERE id_operacion BETWEEN :op_ini AND :op_fin
ORDER BY costo_consumo DESC
LIMIT 100;
```

---

## 11) Conclusión final

Este playbook establece una forma estándar de investigar discrepancias financieras en Dashback sin mezclar capas.

Regla de oro:

- **WAC mal** ⇒ **COGS mal** ⇒ **Pour Cost mal**.

Por tanto, el diagnóstico eficiente siempre va de abajo hacia arriba:  
**cantidades → valorización (WAC) → COGS → ratio ejecutivo (Pour Cost)**.
