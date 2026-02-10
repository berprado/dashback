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

# Explicación de la Trazabilidad de Datos

Este mapa de origen describe el **flujo de transformación de datos** que va desde las recetas base hasta el resumen ejecutivo de márgenes y rentabilidad. Es una arquitectura de datos en **capas sucesivas**, donde cada vista se construye sobre la anterior, refinando y enriqueciendo la información.

El proceso comienza con las **recetas y cantidades vendidas**, que son los datos más básicos: qué productos se vendieron y qué ingredientes se necesitan para prepararlos según las fórmulas definidas. Esta información fundamental alimenta todo el análisis posterior.

La vista `vw_combo_detalle_operacion` actúa como el **primer nivel de agregación**, combinando los datos de ventas (comandas) con los detalles de productos y sus componentes. Aquí se resuelven casos especiales como combos o productos compuestos, desagregándolos en sus elementos individuales para un análisis más preciso.

`vw_consumo_insumos_operativa` realiza una **validación de sanidad de cantidades**, asegurando que los cálculos de consumo de ingredientes sean coherentes y estén dentro de rangos esperados. Esta capa actúa como punto de control de calidad de datos antes de aplicar valorización económica.

Con `vw_consumo_valorizado_operativa` se introduce el **componente financiero**: cada insumo consumido se multiplica por su costo unitario (probablemente usando el método WAC - Weighted Average Cost), generando el costo real por producto vendido. Esta es la capa crítica donde el inventario físico se convierte en cifras monetarias.

`vw_cogs_comanda` (Cost of Goods Sold por comanda) **agrega todos los costos** a nivel de cada venta individual, sumando el costo de todos los productos que componían esa comanda. Aquí ya tenemos el COGS real de cada transacción.

`vw_margen_comanda` **cruza ventas con costos**: toma el monto de venta de cada comanda (desde `comandas_v6` u otra fuente) y le resta el COGS calculado, obteniendo el margen bruto por comanda. Aquí se pueden calcular también porcentajes de margen y otros KPIs a nivel transaccional.

Finalmente, el **resumen ejecutivo** consolida toda esta información en métricas agregadas: ventas totales, COGS totales y márgenes por período, operación, categoría de producto, etc. Esta última capa es la que típicamente se presenta en el dashboard para la toma de decisiones estratégicas.

Este diseño en cascada permite **auditar y diagnosticar** problemas en cualquier nivel: si el margen final parece incorrecto, puedes rastrear hacia atrás a través de cada vista hasta identificar si el problema está en las recetas, los costos unitarios, las cantidades vendidas o algún error de cálculo intermedio.