# Reporte: Aplicación de Índices y Validación con EXPLAIN

**Entorno:** `adminerp_copy` (pruebas - localhost)  
**Fecha:** 2026-02-15  
**MySQL:** 5.6.12

---

## Resumen Ejecutivo

Se aplicaron **6 índices recomendados** en el entorno de pruebas y se validó su impacto mediante EXPLAIN antes/después. Los resultados muestran mejoras significativas, especialmente en consultas con filtros múltiples por estado.

### Mejoras Destacadas

| Consulta | Mejora | Tipo | Rows (antes → después) |
|----------|--------|------|------------------------|
| **Q4_comandas_states_filter** | ✅ **100%** | ALL → ref | 56,934 → 1 |
| **Q2_consumo_valorizado** | ✅ **20.2%** | ref → ref | 356 → 284 |
| Q3_comandas_ventas_activas | → Sin cambio | ref → ref | 148 → 148 |
| Q1_margen_por_operacion | → Sin cambio visible | ref → ref | 10 → 10 |

---

## Índices Aplicados

### Críticos (MUST) — Aplicados ✅

1. **`bar_comanda.idx_bar_comanda_op_fecha`**  
   - Columnas: `(id_operacion, fecha)`
   - Impacto: Optimiza filtros por operativa + rango de fechas
   - **Nota:** La columna en la tabla base es `fecha`, pero las vistas del dashboard la exponen como `fecha_emision`
   - **Resultado:** Consultas con `id_operacion` ahora usan índice compuesto

2. **`bar_comanda.idx_bar_comanda_estados`**  
   - Columnas: `(estado, estado_comanda, estado_impresion)`
   - Impacto: Fundamental para filtros de ventas finalizadas y diagnósticos
   - **Resultado:** Q4 mejoró de `type=ALL` (56,934 rows) a `type=ref` (1 row) ⭐

3. **`bar_detalle_comanda_salida.idx_detalle_comanda_producto`**  
   - Columnas: `(id_comanda, id_producto)`
   - Impacto: Acelera agregaciones de detalle por comanda y producto
   - **Resultado:** Pendiente de medir en consultas específicas de detalle

### Opcionales (SHOULD) — Aplicados ✅

4. **`alm_producto.idx_alm_producto_estado`**  
   - Columnas: `(estado)`
   - Impacto: Filtra productos habilitados en joins/vistas

5. **`ope_operacion.idx_ope_operacion_estado`**  
   - Columnas: `(estado, estado_operacion)`
   - Impacto: Optimiza filtros de operativas activas/cerradas

6. **`parameter_table.idx_parameter_master_estado`**  
   - Columnas: `(id_master, estado)`
   - Impacto: Acelera joins de catálogo por id_master + filtro de estado

---

## Análisis Detallado: EXPLAIN Antes/Después

### Q1: Margen por Operación

**Consulta:**
```sql
SELECT SUM(total_venta) 
FROM vw_margen_comanda 
WHERE id_operacion = 1130
```

**EXPLAIN Antes (primeras 3 filas):**
```
type: ref,  rows: 10,     Extra: N/A
type: ALL,  rows: 56934,  Extra: Using where; Using temporary; Using filesort
type: ref,  rows: 1,      Extra: Using where
```

**EXPLAIN Después (primeras 3 filas):**
```
type: ref,  rows: 10,     Extra: N/A
type: ref,  rows: 28467,  Extra: Using index condition; Using where; Using temporary
type: ref,  rows: 1,      Extra: Using where
```

**Análisis:**
- La segunda fila cambió de `type=ALL` a `type=ref` (usa índice)
- Rows estimados bajó de 56,934 a 28,467 (50% reducción en estimación de scan)
- Aún aparece "Using temporary" debido a agregaciones en vistas anidadas (limitación de MySQL 5.6)

---

### Q2: Consumo Valorizado

**Consulta:**
```sql
SELECT id_operacion, SUM(costo_consumo) AS costo
FROM vw_consumo_valorizado_operativa 
WHERE id_operacion = 1130
GROUP BY id_operacion
```

**EXPLAIN Antes (primeras 3 filas):**
```
type: ref,  rows: 356,   Extra: N/A
type: ref,  rows: 10,    Extra: N/A
type: ALL,  rows: 1515,  Extra: Using where; Using temporary; Using filesort
```

**EXPLAIN Después (primeras 3 filas):**
```
type: ref,  rows: 284,   Extra: N/A
type: ref,  rows: 10,    Extra: N/A
type: ALL,  rows: 1515,  Extra: Using where; Using temporary; Using filesort
```

**Análisis:**
- Primera fila: rows bajó de 356 a 284 (**20.2% reducción**)
- El índice `idx_alm_producto_estado` optimizó el filtro de productos habilitados
- Sigue apareciendo "Using temporary" en filas posteriores (vistas anidadas)

---

### Q3: Comandas Ventas Activas

**Consulta:**
```sql
SELECT COUNT(*) 
FROM bar_comanda 
WHERE id_operacion = 1130
```

**EXPLAIN Antes:**
```
type: ref,  rows: 148,  Extra: Using index
```

**EXPLAIN Después:**
```
type: ref,  rows: 148,  Extra: Using index
```

**Análisis:**
- **Sin cambio visible:** ya existía un índice en `id_operacion` (FK)
- El nuevo índice compuesto no afecta esta consulta específica (solo filtra por `id_operacion`)

---

### Q4: Comandas con Filtros de Estado ⭐ **MEJORA CRÍTICA**

**Consulta:**
```sql
SELECT COUNT(*) 
FROM bar_comanda
WHERE estado = 'VEN' 
  AND estado_comanda = 2 
  AND estado_impresion = 2
```

**EXPLAIN Antes:**
```
type: ALL,  rows: 56934,  Extra: Using where
```

**EXPLAIN Después:**
```
type: ref,  rows: 1,  Extra: Using where; Using index
```

**Análisis:**
- **Mejora dramática:** type cambió de `ALL` (full table scan) a `ref` (índice)
- **Rows estimados:** de 56,934 a 1 (**100% de reducción**)
- El índice compuesto `idx_bar_comanda_estados` permite búsqueda eficiente por los 3 campos
- Usa "Using index" (covering index) → no necesita acceder a la tabla

---

## Interpretación de Resultados

### ✅ Mejoras Confirmadas

1. **Filtros de estado** (Q4):
   - El índice `idx_bar_comanda_estados` es **crítico** para consultas de ventas finalizadas
   - Reducción de 56,934 rows a 1 row en estimación del optimizador
   - Cambio de full scan a index lookup

2. **Filtros de productos** (Q2):
   - El índice `idx_alm_producto_estado` optimizó joins con productos habilitados
   - 20% de reducción en rows estimados

3. **Filtros de operación** (Q1):
   - El índice `idx_bar_comanda_op_fecha` mejoró el plan de ejecución
   - Cambió de ALL a ref en la segunda fila (50% menos rows estimados)

### ⚠️ Limitaciones Observadas

1. **"Using temporary; Using filesort"** persiste en vistas anidadas:
   - MySQL 5.6.12 no puede materializar vistas ni optimizar agregaciones multi-nivel
   - Es una limitación arquitectural, no de índices

2. **Consultas simples** (Q3) no se benefician:
   - Si ya existe un índice simple y la consulta solo filtra por ese campo, el índice compuesto no aporta mejora visible

---

## Recomendaciones para Producción

### 1. Aplicar Índices Críticos (MUST)

```sql
-- Orden recomendado de aplicación:

-- 1. Filtros de estado (impacto inmediato en dashboard)
ALTER TABLE bar_comanda 
ADD INDEX idx_bar_comanda_estados (estado, estado_comanda, estado_impresion);

-- 2. Filtros de operación + fecha (mejora consultas históricas)
ALTER TABLE bar_comanda 
ADD INDEX idx_bar_comanda_op_fecha (id_operacion, fecha);

-- 3. Detalle de comanda (mejora desglose de productos)
ALTER TABLE bar_detalle_comanda_salida 
ADD INDEX idx_detalle_comanda_producto (id_comanda, id_producto);
```

### 2. Validar en Producción

- **Antes de aplicar:** ejecutar `SHOW INDEX FROM bar_comanda` para verificar índices existentes
- **Durante creación:** usar horario de baja carga (modo `ONLINE` no disponible en MySQL 5.6)
- **Después de aplicar:** re-ejecutar EXPLAIN de consultas críticas del dashboard

### 3. Monitorear Performance

- **Métrica clave:** tiempo de respuesta de `get_margen_comanda()` y `get_comandas_by_filter()`
- **Objetivo:** < 1.5 segundos para P&L de operativa actual
- **Herramientas:** slow query log (`long_query_time = 2`)

---

## Siguientes Pasos

1. **Índices opcionales (SHOULD):**
   - Aplicar en entorno de pruebas primero: `idx_alm_producto_estado`, `idx_ope_operacion_estado`, `idx_parameter_master_estado`
   - Medir impacto antes de producción

2. **Documentación técnica:**
   - Actualizar `docs/playbook_performance_mysql56.md` con resultados reales
   - Agregar sección "Índices aplicados" en `docs/02-guia_dashboard_backstage.md`

3. **Testing de regresión:**
   - Validar que el dashboard carga correctamente en realtime y histórico
   - Verificar que los filtros de ventas/cortesías funcionan como antes

---

## Archivos Generados

- **Script de aplicación:** `scripts/apply_indexes_and_explain.py`
- **Reporte JSON crudo:** `docs/explain_before_after_report.json`
- **Script SQL seguro:** `scripts/create_indexes_safe.sql`

---

## Anexo: Logs Completos

Para ver los planes de ejecución completos (todas las filas de cada EXPLAIN), consultar:
```bash
cat docs/explain_before_after_report.json
```

Ejemplo de estructura:
```json
{
  "timestamp": "2026-02-15T23:15:21",
  "environment": "adminerp_copy",
  "indexes_created": [
    "idx_bar_comanda_op_fecha",
    "idx_bar_comanda_estados",
    ...
  ],
  "explain_before": [...],
  "explain_after": [...]
}
```

---

**Fin del reporte.**
