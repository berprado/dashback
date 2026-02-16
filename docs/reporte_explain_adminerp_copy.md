# 🧪 Reporte EXPLAIN — adminerp_copy (solo lectura)

**Fecha:** 2026-02-15  
**Entorno:** adminerp_copy (pruebas)  
**Alcance:** consultas EXPLAIN sobre vistas financieras y consumo  
**Nota:** no se realizaron cambios en la base de datos.

---

## 1) Consultas evaluadas

```sql
-- P&L consolidado por operativa
EXPLAIN
SELECT SUM(total_venta) AS ventas, SUM(cogs_comanda) AS cogs, SUM(margen_comanda) AS margen
FROM adminerp_copy.vw_margen_comanda
WHERE id_operacion = 1130;

-- P&L por rango de operativas
EXPLAIN
SELECT SUM(total_venta) AS ventas, SUM(cogs_comanda) AS cogs, SUM(margen_comanda) AS margen
FROM adminerp_copy.vw_margen_comanda
WHERE id_operacion BETWEEN 1120 AND 1130;

-- COGS por comanda (top costos)
EXPLAIN
SELECT id_operacion, id_comanda, cogs_comanda
FROM adminerp_copy.vw_cogs_comanda
WHERE id_operacion = 1130
ORDER BY cogs_comanda DESC
LIMIT 50;

-- Consumo valorizado por producto
EXPLAIN
SELECT id_operacion, id_producto, cantidad_consumida_base, wac_operativa, costo_consumo
FROM adminerp_copy.vw_consumo_valorizado_operativa
WHERE id_operacion = 1130
ORDER BY costo_consumo DESC
LIMIT 50;

-- Consumo sin valorar (top cantidades)
EXPLAIN
SELECT id_operacion, id_producto, cantidad_consumida_base
FROM adminerp_copy.vw_consumo_insumos_operativa
WHERE id_operacion = 1130
ORDER BY cantidad_consumida_base DESC
LIMIT 50;
```

---

## 2) Observaciones relevantes (resumen)

- En `vw_margen_comanda` se observa `Using temporary` y `Using filesort` en subconsultas derivadas.
- Hay pasos con `type=ALL` (full scan) sobre `bar_comanda` y derivadas de COGS.
- `vw_cogs_comanda` y `vw_consumo_valorizado_operativa` muestran `Using temporary`/`filesort` al ordenar por costo.
- La estructura en cascada de vistas en MySQL 5.6 tiende a generar planes complejos y temporales.

---

## 3) Causas probables (a partir del DDL)

- Falta de indices compuestos en tablas base:
  - `bar_comanda (id_operacion, fecha)` y `(estado, estado_comanda, estado_impresion)`.
  - `bar_detalle_comanda_salida (id_comanda, id_producto)`.
  - `ope_operacion (estado, estado_operacion)`.
  - `parameter_table (id_master, estado)`.
- La vista `vw_cogs_comanda_combos` fija `id_almacen = 1` y depende de `vw_wac_producto_almacen`, que agrega por `id_almacen` y `id_producto`.

---

## 4) Recomendaciones inmediatas

1. Aplicar el checklist de indices validados en [scripts/indexes_minimos_mysql56.sql](scripts/indexes_minimos_mysql56.sql) (solo tras revisar duplicados).
2. Repetir EXPLAIN luego de indices para confirmar reduccion de `type=ALL` y `Using temporary`.
3. Mantener el monitoreo de performance en [docs/playbook_performance_mysql56.md](docs/playbook_performance_mysql56.md).

---

## 5) Limitaciones

- No se ejecutaron consultas de carga ni benchmarks.
- No se analizo con datos de produccion.
- EXPLAIN no muestra tiempos reales; solo el plan estimado.
