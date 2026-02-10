# Consultas COGS y WAC

Documento tecnico para onboarding. Resume el origen y la trazabilidad de los datos que alimentan costos (COGS), ventas y margen por operativa.

## Glosario

- **COGS** (Cost of Goods Sold): costo de los insumos consumidos para producir lo vendido.
- **WAC** (Weighted Average Cost): costo promedio ponderado de un insumo.
- **Margen**: diferencia entre ventas y COGS, indica rentabilidad bruta.
- **Consumo base**: cantidad de insumo expresada en la unidad de medida base del inventario.
- **P&L**: estado de resultados (Profit & Loss), ventas menos costos.

## Convenciones y alcance

- Las consultas filtran por `id_operacion` (variable de contexto principal).
- Todas las consultas usan el placeholder `:id_operacion` para parametrizacion segura.
- El P&L consolidado considera solo ventas reales (comandas `VENTA`), sin cortesias.
- Las vistas listadas son la fuente oficial; no se deben reinterpretar campos a nivel de UI.

## Consulta de resumen economico de la operativa

**Objetivo**
- Obtener el P&L consolidado de una operativa a partir de `vw_margen_comanda`.

**Campos**
- `ventas`: total facturado en la operativa (solo comandas `VENTA`).
- `cogs`: costo total de insumos consumidos (combos + comandables integrados).
- `margen`: utilidad bruta total, $margen = ventas - cogs$.

**Uso tipico**
- Validacion contra `ope_conciliacion`.
- Fuente base para dashboard financiero y control de rentabilidad global.

```sql
SELECT
    SUM(total_venta)     AS ventas,
    SUM(cogs_comanda)    AS cogs,
    SUM(margen_comanda)  AS margen
FROM vw_margen_comanda
WHERE id_operacion = :id_operacion;
```

---

## Consulta de detalle por comanda

**Objetivo**
- Exponer una fila por comanda con ventas, costo y margen para auditoria.

**Campos**
- `total_venta`
- `cogs_comanda`
- `margen_comanda`

**Uso tipico**
- Deteccion de comandas con margen anomalo.
- Validacion de recetas y WAC por turno, bartender o tipo de comanda.

```sql
SELECT *
FROM vw_margen_comanda
WHERE id_operacion = :id_operacion;
```

---

## Consulta de consumo valorizado de insumos

**Objetivo**
- Ver consumo real de insumos valorizado a nivel de producto.

**Campos**
- `cantidad_consumida_base` (unidades base)
- `wac_operativa` / `wac_global`
- `costo_consumo` (costo total por producto)

**Uso tipico**
- Conciliacion contra inventario fisico.
- Deteccion de mermas, recetas mal definidas o errores de multiplicacion.
- Analisis de costos por producto y soporte a renegociacion con proveedores.

```sql
SELECT *
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = :id_operacion;
```

---

## Consumo sin valorar (sanidad de cantidades)

**Objetivo**
- Aislar la consistencia de cantidades sin introducir el costo.

**Criterio de diagnostico**
- Si el consumo es incorrecto aqui, el problema es de receta, unidades o multiplicacion, no de WAC ni de margen.

```sql
SELECT *
FROM vw_consumo_insumos_operativa
WHERE id_operacion = :id_operacion;
```

---

## COGS por comanda (sin ventas)

**Objetivo**
- Exponer costo puro por comanda, sin precio de venta.

**Uso tipico**
- Cortesias (no tienen venta, pero si COGS).
- Auditoria de consumo puro y comparacion con ventas.

```sql
SELECT *
FROM vw_cogs_comanda
WHERE id_operacion = :id_operacion;
```

---

## Trazabilidad de datos (mapa de origen)

1. Recetas + cantidades vendidas
2. `vw_combo_detalle_operacion`
3. `vw_consumo_insumos_operativa` (sanidad de cantidades)
4. `vw_consumo_valorizado_operativa` (costo por producto)
5. `vw_cogs_comanda`
6. `vw_margen_comanda`
7. Resumen ejecutivo (ventas / cogs / margen)

