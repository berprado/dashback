# 🔴 INVESTIGACIÓN: Inconsistencias en WAC/COGS - Estado Actual

**Fecha:** 2026-02-17  
**Responsable:** Auditoría de ambientes

---

## 📌 Resumen Ejecutivo

Se identificaron **3 inconsistencias críticas** en la documentación y posiblemente en los datos de producción:

| ID | Hallazgo | Severidad | Estado | Acción |
|----|----------|-----------|--------|--------|
| INC-001 | Contradicción sobre fuente de WAC | 🔴 CRÍTICA | Pendiente validación | Ejecutar auditoría SQL |
| INC-002 | Alias confuso `wac_operativa` vs `wac_global` | 🟡 MEDIA | Documentado | Aclarar en documentación |
| INC-003 | Cambios del Documento_Maestro en producción desconocidos | 🔴 CRÍTICA | Pendiente validación | Ejecutar auditoría SQL |

---

## 🔴 INCONSISTENCIA 1: Fuente de WAC

### Problema Detectado

**Documento A** (`docs/wac_cogs/guia_tecnica_wac_cogs.md`):
```
"La fuente única de verdad para el costo unitario es la vista 
vw_wac_producto_almacen"
```

**Documento B** (`docs/wac_cogs/Documento_Maestro_COGS_WAC_BackStage_ACTUALIZADO.md`):
```
"Se utiliza ahora vw_wac_global_producto como única fuente de costo unitario
(en vv_cogs_comanda_combos)"
```

### Análisis en adminerp_copy

Cuando se auditó el DDL real:

| Vista | Fuente de Datos | Cálculo |
|-------|-----------------|---------|
| `vw_wac_producto_almacen` | `alm_detalle_ingreso + alm_ingreso` | ✅ Calcula WAC desde ingresos históricos |
| `vw_wac_global_producto` | `vw_costo_heredado_producto` | ⚠️ Toma WAC de otra vista (refactorización antigua) |

### Conclusión Preliminar

- **vw_wac_producto_almacen** es la correcta (calcula desde datos reales)
- **vw_wac_global_producto** es una refactorización ANTIGUA que NO debería usarse
- El Documento_Maestro está **DESFASADO**

### Riesgo

Si el código actual usa `vw_wac_global_producto` en producción, pero pruebas usa `vw_wac_producto_almacen`:
- ❌ Los márgenes/COGS serán DIFERENTES entre ambientes
- ❌ El dashboard mostrará datos INCORRECTOS

### Validación Requerida

✅ Ejecutar `audit_wac_cogs_ddl_consistency.sql` en AMBOS ambientes para confirmar

---

## 🟡 INCONSISTENCIA 2: Alias Confuso

### Problema

En `vw_consumo_valorizado_operativa` aparece:
```sql
SELECT 
    wac_operativa,   -- ¿Diferente a wac_global?
    ...
```

### Análisis

**Hallazgo:** `wac_operativa` es solo un **alias** de `wac_global` (de `vw_wac_producto_almacen` con `id_almacen=1`)

**Muy confuso nombrar:** Parece ser "WAC por operación" pero es en realidad "WAC global"

### Impacto

- 🟡 **BAJO:** El dato es correcto, solo el nombre es confuso
- Puede causar confusión en futuros desarrolladores
- No afecta los números, solo la semántica

### Solución

Renombrar en la vista:
```sql
-- ACTUAL-CONFUSO:
wac_operativa

-- PROPUESTO-CLARO:
wac_global
```

---

## 🔴 INCONSISTENCIA 3: Cambios en Documento_Maestro

### Problema Principal

El `Documento_Maestro_COGS_WAC_BackStage_ACTUALIZADO.md` menciona cambios realizados para "corregir duplicación de costos":

**Cambios afirmados:**
1. Eliminación de fuente que generaba multiplicación por lote
2. Cambio a `vw_wac_global_producto` como única fuente
3. Corrección de COGS por comanda

**Pregunta crítica:** ¿Estos cambios fueron aplicados en producción (`adminerp`)?

### Por Qué Importa

**Escenario A:** Si los cambios SÍ fueron aplicados:
- Producción ya usa `vw_wac_global_producto`
- Pruebas (si sincronizadas bien) debería coincidir

**Escenario B:** Si los cambios NO fueron aplicados:
- Producción sigue con el código antiguo
- Dashboard mostrará datos DIFERENTES entre ambientes

### Validación Requerida

Ejecutar `audit_wac_cogs_ddl_consistency.sql` para:
1. Ver qué vista usa cada ambiente realmente
2. Comparar números de COGS/margen
3. Confirmar si son iguales o diferentes

---

## 🛠️ Plan de Validación (YA PREPARADO)

Se creó un **script de auditoría SQL completo** en:
```
scripts/audit_wac_cogs_ddl_consistency.sql
```

### Qué hace:

1. ✅ Verifica existencia de todas las vistas
2. ✅ Audita DDL (estructura) de vistas críticas
3. ✅ Valida coincidencia de datos entre ambientes
4. ✅ Identifica anomalías (COGS muy altos, comandas sin COGS, etc.)

### Instrucciones:

Ver: `docs/GUIA_AUDITORIA_WAC_COGS.md`

---

## 📊 Matriz de Decisión

### DESPUÉS de ejecutar la auditoría:

```
┌─────────────────────────────────────────────────────────┐
│                    RESULTADO AUDITORÍA                  │
└─────────────────────────────────────────────────────────┘

    ┌─ ¿Vistas iguales en ambos ambientes?
    │
    ├─ SÍ ──────┐
    │           │
    │           └─ ¿Números iguales (margen, COGS)?
    │               │
    │               ├─ SÍ ──────→ ✅ APROBADO - Avanzar con índices
    │               │
    │               └─ NO ──────→ ❌ DEBE INVESTIGAR
    │  
    └─ NO ─────→ ❌ DEBE INVESTIGAR
```

### Si resultado = ✅ APROBADO:

1. Ambientes son consistentes
2. Dashboard será confiable en producción
3. **Es seguro aplicar índices**

### Si resultado = ❌ DEBE INVESTIGAR:

1. Documentar exactamente qué es diferente
2. Investigar por qué es diferente
3. Aplicar cambios para sincronizar si es necesario
4. **NO aplicar índices hasta resolver**

---

## 📋 Checklist: Antes de Ejecutar Auditoría

- [ ] Script `audit_wac_cogs_ddl_consistency.sql` existe
- [ ] Guía de ejecución `GUIA_AUDITORIA_WAC_COGS.md` revisada
- [ ] Acceso a adminerp_copy verificado
- [ ] Acceso a adminerp vía tunel localtonet verificado
- [ ] Carpeta `docs/auditorias/` existe
- [ ] Listo para ejecutar

---

## 🚀 Próximos Pasos

1. **Ejecutar auditoría** siguiendo la guía
2. **Guardar resultados** en `docs/auditorias/`
3. **Comparar** ambiente pruebas vs producción
4. **Documentar hallazgos** en `ANALISIS_COMPARATIVO_2026-02-17.md`
5. **Confirmar conmigo** antes de aplicar índices

---

## 📚 Archivos Relacionados

- [scripts/audit_wac_cogs_ddl_consistency.sql](../scripts/audit_wac_cogs_ddl_consistency.sql) - Script de auditoría
- [docs/GUIA_AUDITORIA_WAC_COGS.md](../docs/GUIA_AUDITORIA_WAC_COGS.md) - Guía paso a paso
- [docs/analisis_wac_cogs_margenes.md](../docs/analisis_wac_cogs_margenes.md) - Análisis técnico completo
- [docs/reporte_indices_aplicados.md](../docs/reporte_indices_aplicados.md) - Reporte de índices aplicados

---

**Última actualización:** 2026-02-17  
**Estado:** ⏳ Pendiente ejecución de auditoría
