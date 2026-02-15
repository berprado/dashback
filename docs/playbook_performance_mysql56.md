# ⚙️ Playbook de Performance — MySQL 5.6.12 (Dashback)

> Objetivo: asegurar consultas estables y rapidas en el stack de vistas de WAC/COGS/margenes.
> Alcance: consultas desde Streamlit a vistas SQL en MySQL 5.6.12.

---

## 1) Principios base para MySQL 5.6.12

- Las vistas **no se materializan**; cada consulta expande el plan completo.
- Evitar funciones en columnas filtradas (`DATE(fecha_emision)`), porque deshabilitan indices.
- `COUNT(DISTINCT ...)` puede ser costoso; preagregar por `id_comanda` cuando aplique.
- Preferir `UNION ALL` cuando no se requiere deduplicacion (ya aplicado en COGS).
- Limitar resultados con `LIMIT` y ordenar solo cuando el usuario lo pide.

---

## 2) Checklist de diagnostico rapido

- Confirmar que la vista consultada existe en la DB activa.
- Revisar filtros aplicados (operativas o fechas) y que usen columnas indexadas.
- Ejecutar `EXPLAIN` para cada consulta critica y buscar:
  - `type=ALL` (full scan) en tablas grandes.
  - `rows` muy altos sin filtro.
  - `Using temporary` / `Using filesort` en agregaciones grandes.
- Validar que `id_operacion` y `fecha_emision` no esten envueltas en funciones.

---

## 3) Set de consultas EXPLAIN recomendado

```sql
-- P&L consolidado por operativa
EXPLAIN
SELECT
    SUM(total_venta) as ventas,
    SUM(cogs_comanda) as cogs,
    SUM(margen_comanda) as margen
FROM vw_margen_comanda
WHERE id_operacion = 1234;

-- P&L por rango de fechas
EXPLAIN
SELECT
    SUM(total_venta) as ventas,
    SUM(cogs_comanda) as cogs,
    SUM(margen_comanda) as margen
FROM vw_margen_comanda
WHERE fecha_emision BETWEEN '2026-02-01 00:00:00' AND '2026-02-15 23:59:59';

-- COGS por comanda (top costos)
EXPLAIN
SELECT
    id_operacion,
    id_comanda,
    cogs_comanda
FROM vw_cogs_comanda
WHERE id_operacion = 1234
ORDER BY cogs_comanda DESC
LIMIT 50;

-- Consumo valorizado por producto
EXPLAIN
SELECT
    id_operacion,
    id_producto,
    cantidad_consumida_base,
    wac_operativa,
    costo_consumo
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1234
ORDER BY costo_consumo DESC
LIMIT 50;
```

---

## 4) Checklist de indices minimos (tabla base)

> Este checklist esta pensado para MySQL 5.6.12. Ajustar a DDL real.

**bar_comanda**
- `(id_operacion, fecha_emision)`
- `(estado, estado_comanda, estado_impresion)`
- `(id)`

**bar_detalle_comanda_salida**
- `(id_comanda, id_producto)`
- `(fecha_emision)` si existe

**alm_ingreso**
- `(id_producto)`
- `(fecha_ingreso)` si aplica

**alm_producto**
- `(estado)` si se filtra por `estado='HAB'`

**ope_operacion**
- `(estado, estado_operacion)`

**parameter_table**
- `(id_master, estado)`

---

## 5) Acciones de mejora sugeridas

1. **Preagregar P&L para operativas cerradas**
   - Materializar resultados por `id_operacion` y refrescar bajo demanda.

2. **Separar consumo base vs consumo valorizado**
   - Crear una vista base de cantidades y derivar valorizado con JOIN a WAC.

3. **Evitar full scans en historico**
   - Asegurar indices en `fecha_emision` y filtrar por rango sin funciones.

4. **Reducir COUNT(DISTINCT) repetidos**
   - Preagregar por `id_comanda` en subvista si hay latencia.

---

## 6) Criterios de aceptacion (performance)

- P&L consolidado por operativa: < 1.5s en operativas cerradas promedio.
- P&L por rango de fechas (7 dias): < 3s.
- Consumo valorizado (top 50): < 2s.
- Sin `type=ALL` en tablas grandes en las consultas criticas.

---

## 7) Notas operativas

- En produccion, usar credenciales read-only.
- Documentar cualquier cambio de indices o vistas en [docs/03-evolucion_y_mejoras.md](docs/03-evolucion_y_mejoras.md).
- Mantener el analisis financiero centralizado en [docs/analisis_wac_cogs_margenes.md](docs/analisis_wac_cogs_margenes.md).
