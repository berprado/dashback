# Runbook rápido: diagnóstico WAC / COGS / Pour Cost

**Fecha de creación:** 2026-02-20  
**Objetivo:** guía corta para detectar rápidamente por qué difieren WAC, COGS o Pour Cost entre Local (prueba) y Producción.

---

## 1) Regla principal (orden correcto)

Diagnostica en este orden:

1. **Cantidades** (consumo sin valorar)
2. **Valorización** (WAC aplicado)
3. **COGS por comanda**
4. **P&L y Pour Cost**

Si falla una capa, **no avances** a la siguiente hasta resolverla.

---

## 2) Checklist de arranque (2 minutos)

- [ ] Misma conexión lógica en ambos lados (`mysql` vs `mysql_prod` controlado).
- [ ] Misma base activa confirmada (`DATABASE()`).
- [ ] Mismo contexto de filtro (`ops` o `dates`).
- [ ] Misma operativa o rango exacto.
- [ ] Existen vistas críticas:
  - `vw_consumo_insumos_operativa`
  - `vw_consumo_valorizado_operativa`
  - `vw_cogs_comanda`
  - `vw_margen_comanda`

---

## 3) Señales rápidas y diagnóstico

### Caso A: falla consumo sin valorar

- Síntoma: cantidades distintas por producto/comanda.
- Causa probable: receta, unidades o multiplicación.
- Responsable sugerido: Operaciones + Datos.

### Caso B: sin valorar cuadra, valorizado no

- Síntoma: cantidad igual, costo diferente.
- Causa probable: WAC/costo inventario distinto entre entornos.
- Responsable sugerido: Inventario + DBA/BI.

### Caso C: valorizado cuadra, COGS por comanda no

- Síntoma: costo por producto bien, agregado por comanda mal.
- Causa probable: DDL/lógica de `vw_cogs_comanda` diferente.
- Responsable sugerido: DBA/BI.

### Caso D: COGS cuadra, Pour Cost no

- Síntoma: costo total igual, ratio distinto.
- Causa probable: ventas o filtros distintos en `vw_margen_comanda`.
- Responsable sugerido: BI + Producto.

---

## 4) SQL mínimo de verificación

### 4.1 P&L consolidado (COGS + Pour Cost)

```sql
SELECT
    COALESCE(SUM(total_venta), 0) AS total_ventas,
    COALESCE(SUM(cogs_comanda), 0) AS total_cogs,
    ROUND(
        COALESCE(SUM(cogs_comanda), 0) / NULLIF(COALESCE(SUM(total_venta), 0), 0) * 100,
        2
    ) AS pour_cost_pct
FROM vw_margen_comanda
WHERE id_operacion BETWEEN :op_ini AND :op_fin;
```

### 4.2 COGS por comanda (impacto alto)

```sql
SELECT id_operacion, id_comanda, cogs_comanda
FROM vw_cogs_comanda
WHERE id_operacion BETWEEN :op_ini AND :op_fin
ORDER BY cogs_comanda DESC
LIMIT 100;
```

### 4.3 Consumo valorizado (WAC aplicado)

```sql
SELECT id_operacion, id_producto, cantidad_consumida_base, wac_operativa, costo_consumo
FROM vw_consumo_valorizado_operativa
WHERE id_operacion BETWEEN :op_ini AND :op_fin
ORDER BY costo_consumo DESC
LIMIT 100;
```

### 4.4 Consumo sin valorar (sanidad base)

```sql
SELECT id_operacion, id_producto, cantidad_consumida_base
FROM vw_consumo_insumos_operativa
WHERE id_operacion BETWEEN :op_ini AND :op_fin
ORDER BY cantidad_consumida_base DESC
LIMIT 100;
```

---

## 5) Definiciones express

- **WAC:** costo unitario promedio ponderado de insumo.
- **COGS:** costo total de insumos consumidos.
- **Pour Cost %:** `(COGS / Ventas) × 100`.

Jerarquía:

\[
WAC \rightarrow COGS \rightarrow Pour\ Cost
\]

---

## 6) Cierre del incidente (criterios de salida)

Marcar incidente como resuelto solo si:

- [ ] Coinciden cantidades (sin valorar).
- [ ] Coincide valorización (WAC/costo).
- [ ] Coincide COGS por comanda y total.
- [ ] Coincide Pour Cost para el mismo rango.
- [ ] Se documentó causa raíz y capa donde se originó.
