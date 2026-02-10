---
name: mysql-dashback
description: Lineamientos para escribir, depurar y optimizar consultas MySQL 5.6 read-only para dashboards Streamlit. Usar cuando se trabaje con consultas SQL para el dashboard, se diagnostiquen discrepancias en estados o se optimicen queries de vistas. Cubre parametrización segura, patrones de agregación, diagnóstico vista-vs-tabla, y buenas prácticas para evitar locks en producción.
---

# MySQL Read-Only para Dashboards

Guía práctica para consultas MySQL 5.6.x en dashboards Streamlit, enfocada en seguridad, rendimiento y diagnóstico.

## Reglas Fundamentales

| Regla | Descripción |
|-------|-------------|
| **Read-only** | Solo `SELECT`. Nunca `INSERT`, `UPDATE`, `DELETE`, `DDL` |
| **Sin locks pesados** | Evitar `SHOW CREATE VIEW`, `ALTER VIEW` en horario operativo |
| **Sin esquema hardcodeado** | Usar nombres no calificados (sin `adminerp.` o `adminerp_copy.`) |
| **Siempre limitar** | Usar `ORDER BY ... DESC LIMIT n` en inspecciones de detalle |
| **NULL ≠ valor por defecto** | `NULL` indica dato no persistido, no asumir que significa "PENDIENTE" |

## Parametrización

Usar placeholders estilo SQLAlchemy (`:param`). La capa de ejecución convierte a `%(param)s` cuando corresponde.

```sql
-- ✅ Correcto
SELECT * FROM vista WHERE id_operacion BETWEEN :op_ini AND :op_fin;

-- ❌ Incorrecto (interpolación directa)
SELECT * FROM vista WHERE id_operacion BETWEEN {op_ini} AND {op_fin};
```

## Patrones de Consulta

### Conteos por Estado

Usar `COUNT(DISTINCT id)` para contar entidades únicas cuando la vista tiene múltiples filas por entidad (ej: ítems por comanda).

```sql
SELECT
    COUNT(DISTINCT CASE WHEN estado = 'PENDIENTE' THEN id END) AS pendientes,
    COUNT(DISTINCT CASE WHEN estado = 'ANULADO' THEN id END) AS anulados,
    COUNT(DISTINCT CASE WHEN estado IS NULL THEN id END) AS sin_estado
FROM vista
WHERE id_operacion = :op;
```

### Inspección de Detalle (Top N)

Siempre ordenar descendente y limitar para obtener los más recientes.

```sql
SELECT DISTINCT id
FROM vista
WHERE id_operacion = :op
  AND estado <> 'ANULADO'
ORDER BY id DESC
LIMIT 50;
```

### Diagnóstico Vista vs Tabla Base

Cuando la vista muestra un valor diferente al esperado, comparar múltiples fuentes.

```sql
SELECT
    v.id,
    v.estado AS estado_vista,
    t.estado AS estado_tabla,
    CASE 
        WHEN v.estado = t.estado THEN 'OK'
        WHEN v.estado IS NULL AND t.estado IS NOT NULL THEN 'VISTA_NULL'
        WHEN v.estado IS NOT NULL AND t.estado IS NULL THEN 'TABLA_NULL'
        ELSE 'DIFERENTE'
    END AS diagnostico
FROM (
    SELECT id, MAX(estado) AS estado
    FROM vista
    WHERE id IN (/* lista de IDs */)
    GROUP BY id
) v
LEFT JOIN tabla_base t ON t.id = v.id
ORDER BY v.id DESC;
```

### JOINs con Catálogos (parameter_table)

Siempre filtrar por `id_master` y `estado='HAB'` para evitar duplicados y registros deshabilitados.

```sql
-- ✅ Correcto
LEFT JOIN parameter_table pt
    ON pt.id = t.estado_id
   AND pt.id_master = 10
   AND pt.estado = 'HAB'

-- ❌ Incorrecto (puede traer duplicados o registros deshabilitados)
LEFT JOIN parameter_table pt
    ON pt.id = t.estado_id
```

## Agregaciones Temporales

Para métricas por entidad (no por ítem), agrupar primero.

```sql
-- Timestamp único por entidad
SELECT
    id,
    MIN(fecha) AS primera_fecha,
    MAX(fecha) AS ultima_fecha
FROM vista
WHERE id_operacion = :op
GROUP BY id
ORDER BY ultima_fecha DESC
LIMIT 100;
```

## Checklist Pre-Ejecución

Antes de considerar válido un resultado, verificar:

- [ ] ¿Estoy consultando la base de datos correcta? (`SELECT DATABASE()`)
- [ ] ¿Estoy usando la vista correcta? (real-time vs histórico)
- [ ] ¿La consulta respeta los filtros estándar? (operación o fechas)
- [ ] ¿Los JOINs a catálogos filtran `id_master` y `estado`?
- [ ] ¿Hay `LIMIT` si es inspección de detalle?
- [ ] ¿Las agregaciones usan `COUNT(DISTINCT id)` cuando corresponde?

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Conteo duplicado | `COUNT(*)` en vista con múltiples filas por entidad | Usar `COUNT(DISTINCT id_entidad)` |
| Resultados vacíos inesperados | Vista real-time vacía fuera de horario | Verificar con vista histórica |
| Estado NULL inesperado | Dato no persistido aún en tabla base | Verificar tabla base y logs |
| Duplicados en JOIN | `parameter_table` sin filtro `id_master` | Agregar filtro `id_master` y `estado='HAB'` |
| Timeout | Query sin `LIMIT` en vista grande | Agregar `LIMIT` y `WHERE` acotado |

## Rendimiento

- Preferir agregaciones sobre `COUNT(DISTINCT id)` vs contar filas
- Evitar `ORDER BY` sin `LIMIT` en vistas grandes
- Para queries pesadas, ejecutar bajo demanda (checkbox/botón en UI)
- En producción, evitar consultas de estructura (`SHOW CREATE VIEW`) durante operación

## Interpretación de Estados NULL

| Contexto | NULL significa |
|----------|----------------|
| Vista | Dato aún no persistido por el sistema fuente |
| Tabla base | Campo no poblado (posible bug o estado intermedio) |
| Log | No existe registro de la acción |
| Vista + Tabla + Log = NULL | El sistema fuente aún no procesó la entidad |
