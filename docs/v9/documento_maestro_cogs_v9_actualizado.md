# 🧠 Documento Maestro COGS Consolidado BackStage V9 (Actualizado)

## Modelo Dual: Venta vs Consumo + Flujo WAC → COGS

---

# 1. 🎯 Propósito

Este documento define el modelo financiero oficial del sistema BackStage:

- Cálculo de COGS real
- Determinación de márgenes
- Separación de dimensiones:
  - Venta
  - Consumo
- Flujo completo desde WAC hasta KPI

---

# 2. 🧩 Modelo Dual

## 🔷 Dimensión de Venta
- Fuente: v9_item_base
- Categoría: categoria_item_venta
- Nivel: item vendido

## 🔶 Dimensión de Consumo
- Fuente: comandas_v9_detallada
- Categoría: categoria_receta
- Nivel: ingrediente

---

# ⚠️ Regla Fundamental

Venta ≠ Consumo

---

# 3. 🏗️ Arquitectura

RAW → comandas_v7 → comandas_v8 → comandas_v9_detallada → v9_item_base → KPI

---

# 4. 🧠 Flujo Financiero Completo

## 4.1 Determinación del WAC

Tabla: cache_wac_producto  
Trigger: trg_wac_after_insert_detalle  

Reglas:

- Precio 0 → no afecta WAC  
- Stock 0 → WAC = precio nuevo  
- Stock > 0 → promedio ponderado incremental  

---

## 4.2 Flujo de Costos

### Paso 1 — Ingreso
alm_detalle_ingreso → actualiza WAC

### Paso 2 — Consumo
comandas_v8 → cantidades

### Paso 3 — Costeo
comandas_v9_detallada

costo_total_linea = cantidad_consumida_unidad_base × WAC

### Paso 4 — Consolidación
v9_item_base

cogs_item = SUM(costo_total_linea)

### Paso 5 — KPI
v9_kpi_operativa

cogs_total = SUM(cogs_item)

---

# 5. 📊 Vistas Principales

## Base
- comandas_v7
- comandas_v8

## Core
- comandas_v9_detallada

## Item
- v9_item_base

## KPI
- v9_kpi_operativa
- v9_kpi_venta_categoria
- v9_kpi_consumo_categoria

---

# 6. 📊 Definiciones

Venta Real → ingreso efectivo  
Venta Teórica → antes de cortesías  
COGS → costo real  
Margen → venta - costo  
Pour Cost → costo / venta  

---

# 7. 🎯 Capacidades

- Margen por producto
- Análisis de categorías
- Control de consumo
- Pricing estratégico

---

# 8. 🚨 Reglas de Oro

- Nunca sumar ventas desde detalle  
- Nunca mezclar dimensiones  
- No hacer JOIN con KPI  

---

# 9. 🏁 Conclusión

El modelo V9 es:

✔ consistente  
✔ auditable  
✔ escalable  
✔ listo para BI  

---

# 🔥 Frase Final

El costo no se estima  
El costo se reconstruye
