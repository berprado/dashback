# Consultas COGS y WAC

## Consulta de resumen económico de la operativa

**Qué hace**
- Entrega el P&L consolidado de la operativa (solo ventas reales, sin cortesías).

**Campos**
- `ventas`: Suma todo lo facturado en la operativa (comandas VENTA).
- `cogs`: Suma el costo total de los insumos consumidos (combos + comandables si ya están integrados).
- `margen`: Utilidad bruta total = ventas − cogs.

**Para qué sirve**
- Validación contra `ope_conciliacion`.
- Base directa para dashboard financiero.
- Base directa para margen por día / operativa.
- Base directa para control de rentabilidad global.

👉 Esta es la consulta ejecutiva. La que mira el dueño.

```sql
SELECT
    SUM(total_venta)     AS ventas,
    SUM(cogs_comanda)    AS cogs,
    SUM(margen_comanda)  AS margen
FROM vw_margen_comanda
WHERE id_operacion = 1125;
```

---

## Consulta de detalle por comanda

**Qué hace**
- Devuelve una fila por comanda.

**Campos**
- `total_venta`
- `cogs_comanda`
- `margen_comanda`

**Para qué sirve**
- Auditoría fina para detectar comandas con margen anómalo.
- Auditoría fina para detectar errores de receta / WAC.
- Análisis operativo sobre qué tipo de comandas generan mejor margen.
- Análisis operativo sobre qué bartender / turno vende mejor.

👉 Esta es la consulta táctica. La que mira el jefe de barra.

```sql
SELECT *
FROM vw_margen_comanda
WHERE id_operacion = 1125;
```

---

## Consulta de consumo valorizado de insumos

**Qué hace**
- Muestra qué insumos se consumieron realmente, agregados por producto.

**Campos**
- `cantidad_consumida_base` (en unidades base)
- `wac_operativa` / `wac_global`
- `costo_consumo` total por producto

**Para qué sirve**
- Conciliar contra inventario físico.
- Detectar mermas.
- Detectar recetas mal definidas.
- Detectar errores de multiplicación de cantidades.
- Base para análisis de costos por producto.
- Base para renegociación con proveedores.

👉 Esta es la consulta logística. La que mira inventarios y control.

```sql
SELECT *
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1125;
```

---

## Consumo sin valorar (sanidad de cantidades)

**Por qué es clave**
- Aísla el problema de cantidades del problema de costos.
- Si algo está mal aquí: no es WAC, no es margen, es receta / multiplicación / unidades.

👉 Regla de oro: si el consumo está mal, todo lo demás estará mal aunque el WAC sea perfecto.

```sql
SELECT *
FROM vw_consumo_insumos_operativa
WHERE id_operacion = 1125;
```

---

## COGS por comanda (sin ventas)

**Para qué sirve**
- Ver solo el costo, sin precio de venta.
- Ideal para cortesías (que no tienen venta pero sí COGS).
- Ideal para auditoría de consumo puro.

👉 Esta consulta es la bisagra entre inventario y finanzas.

```sql
SELECT *
FROM vw_cogs_comanda
WHERE id_operacion = 1125;
```

---

## Mapa mental

1. Recetas + Cantidades vendidas
2. `vw_combo_detalle_operacion`
3. `vw_consumo_insumos_operativa` (sanidad de cantidades)
4. `vw_consumo_valorizado_operativa` (costo por producto)
5. `vw_cogs_comanda`
6. `vw_margen_comanda`
7. Resumen ejecutivo (ventas / cogs / margen)
no es margen



