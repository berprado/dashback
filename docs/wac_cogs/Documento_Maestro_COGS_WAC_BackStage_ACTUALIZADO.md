# 📊 Documento Maestro -- Modelo COGS & WAC (Actualizado)

**Proyecto:** BackStage POS\
**Fecha de actualización:** 2026-02-13 13:09:35

------------------------------------------------------------------------

## 🎯 Objetivo de esta actualización

Corregir la duplicación de costos detectada en el cálculo de COGS por
comanda, manteniendo intactas las tablas originales y ajustando
únicamente la capa de vistas SQL.

------------------------------------------------------------------------

# 🔎 Problema Detectado

El COGS por comanda estaba inflado debido a:

-   Uso incorrecto del WAC proveniente de vistas que devolvían múltiples
    filas por producto.
-   Multiplicación repetida de la cantidad consumida por cada variación
    histórica de costo.
-   Resultado: márgenes negativos en combos rentables y pour cost
    \>100%.

------------------------------------------------------------------------

# ✅ Estrategia de Corrección

Se decidió:

✔ No modificar tablas originales\
✔ No recalcular pasado\
✔ No aplicar FIFO\
✔ Mantener WAC real\
✔ Corregir exclusivamente la vista donde se valorizaba por comanda

------------------------------------------------------------------------

# 🛠 Vistas Modificadas

## 1️⃣ vw_cogs_comanda_combos 🔥 (Vista crítica corregida)

### Cambio realizado:

-   Se eliminó la fuente que generaba multiplicación por lote.
-   Se utiliza ahora `vw_wac_global_producto` como única fuente de costo
    unitario.
-   El cálculo se hace directamente sobre el consumo real por comanda.

### Nueva lógica conceptual:

    SUM(
        cantidad_base * wac_global
    )
    GROUP BY id_operacion, id_comanda, id_barra

Resultado: - Costo correcto por combo. - Sin duplicación. - COGS
coherente con cálculo manual.

------------------------------------------------------------------------

## 2️⃣ vw_cogs_comanda_unificada

Sin cambios estructurales. Recibe ahora datos corregidos desde
`vw_cogs_comanda_combos`.

------------------------------------------------------------------------

## 3️⃣ vw_cogs_comanda

Sin cambios estructurales. Agrupa correctamente por:

    id_operacion, id_comanda, id_barra

------------------------------------------------------------------------

# 📌 Vistas Analizadas (sin modificación)

-   vw_consumo_insumos_operativa
-   vw_consumo_valorizado_operativa
-   vw_wac_global_producto
-   vw_costo_heredado_producto

Estas permanecen intactas.

------------------------------------------------------------------------

# 📊 Resultado Validado

Ejemplo Operación 1130:

Antes: - COGS combo ≈ 1.257 Bs - Margen negativo

Después: - COGS combo ≈ 279.94 Bs - Margen correcto - Pour cost
coherente (\~29-30%) - Margen \>70% en dashboard global

------------------------------------------------------------------------

# 🧠 Arquitectura Final del Flujo

Recetas\
→ vw_combo_detalle_operacion\
→ vw_cogs_comanda_combos (corregida)\
→ vw_cogs_comanda_unificada\
→ vw_cogs_comanda\
→ vw_margen_comanda\
→ Dashboard KPIs

------------------------------------------------------------------------

# 🚀 Estado del Modelo

✔ WAC respetado\
✔ No se recalcula pasado\
✔ COGS estable\
✔ Margen correcto\
✔ Pour cost correcto\
✔ Modelo audit-able

------------------------------------------------------------------------

**Este documento reemplaza la versión anterior en lo referente al
cálculo de COGS por comanda.**
