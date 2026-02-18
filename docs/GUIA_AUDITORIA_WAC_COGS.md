# 🔍 Guía: Auditoría de Consistencia WAC/COGS

**Objetivo:** Verificar que las vistas y datos de WAC/COGS/márgenes son consistentes entre `adminerp_copy` (pruebas) y `adminerp` (producción).

**Duración:** ~15 minutos

**Requisitos:** 
- dbForge Studio (lo que ya tienes)
- Acceso a ambos ambientes

---

## 📋 Paso 1: Preparar el Script

1. Abre [scripts/audit_wac_cogs_ddl_consistency.sql](../scripts/audit_wac_cogs_ddl_consistency.sql)
2. **NO ejecutes aún**

---

## 🔄 Paso 2: Obtener la Operación a Auditar

Primero necesitas identificar qué operación usar como referencia:

### En PRUEBAS (adminerp_copy):

1. Conecta a `adminerp_copy` en dbForge
2. Ejecuta SOLO esta query:

```sql
-- Obtener operación activa (si existe)
SELECT op.id AS id_operacion, op.estado, op.estado_operacion
FROM ope_operacion op
WHERE op.estado = 'HAB' AND op.estado_operacion IN (22, 24)
LIMIT 1;

-- Si no hay activa, obtener la más reciente cerrada
SELECT op.id AS id_operacion, op.estado, op.estado_operacion
FROM ope_operacion op
WHERE op.estado = 'INA'
ORDER BY op.id DESC
LIMIT 1;
```

3. **Anota el `id_operacion` que retorna** (ejemplo: `1130`)

### En PRODUCCIÓN (adminerp):

1. Conecta a `adminerp` vía tunel localtonet en dbForge
2. Ejecuta las mismas 2 queries
3. **Anota ese `id_operacion`** (puede ser diferente)

---

## 🛠️ Paso 3: Personalizar el Script

En el script `audit_wac_cogs_ddl_consistency.sql`:

1. **Busca** todas las instancias de `1130` (hay ~10)
2. **Reemplázalas** con el `id_operacion` que anotaste

### Ejemplo:
```sql
-- ANTES:
WHERE id_operacion = 1130;

-- DESPUÉS (si tu operación es 1145):
WHERE id_operacion = 1145;
```

**Herramienta:** Usa Ctrl+H (Buscar y Reemplazar) en dbForge para hacerlo rápido.

---

## ▶️ Paso 4: Ejecutar en PRUEBAS

1. **Conecta a `adminerp_copy`** en dbForge
2. Abre el script personalizado
3. **Selecciona TODO** el script (Ctrl+A)
4. **Ejecuta** (Click en ▶️ o F5)
5. **Espera** a que termine (15-30 segundos)

### Guardar resultado:

1. Selecciona **TODO el output** (Results panel)
2. Click derecho → **Export to File**
3. Guarda como: `audit_pruebas_2026-02-17.txt`
4. Ubicación: `docs/auditorias/`

---

## ▶️ Paso 5: Ejecutar en PRODUCCIÓN

1. **Conecta a `adminerp`** vía tunel localtonet en dbForge
2. Abre **el MISMO script personalizado**
3. **Selecciona TODO**
4. **Ejecuta**
5. **Espera** a que termine

### Guardar resultado:

1. Selecciona **TODO el output**
2. Click derecho → **Export to File**
3. Guarda como: `audit_produccion_2026-02-17.txt`
4. Ubicación: `docs/auditorias/`

---

## 📊 Paso 6: Comparar Resultados

Abre AMBOS archivos lado a lado.

### ✅ SEÑALES DE QUE TODO ESTÁ BIEN:

- **PARTE 1 (Vistas):** Mismas vistas en ambos ambientes
- **PARTE 2 (DDL):** Todas las vistas existen en ambos
- **PARTE 5 (Margen):** Números **EXACTAMENTE IGUALES**
- **PARTE 6 (Consumo):** Números **EXACTAMENTE IGUALES**
- **PARTE 7 (COGS):** Números **EXACTAMENTE IGUALES**

**Ejemplo de coincidencia perfecta:**
```
PRUEBAS:
total_ventas: 1500.00 | total_cogs: 450.00 | margen_pct: 70.00

PRODUCCIÓN:
total_ventas: 1500.00 | total_cogs: 450.00 | margen_pct: 70.00

✅ MATCH → OK para avanzar
```

### ❌ SEÑALES DE ALA:

- **Vistas diferentes:** "MISSING" en producción pero existe en pruebas
- **Números desiguales:** margen 70% en pruebas vs 65% en producción
- **Anomalías (Parte 10):** Comandas sin COGS o COGS > 1000

**Si encuentras cualquier ❌:**
- **NO avances con índices**
- Documenta exactamente qué es diferente
- Investiga antes de continuar

---

## 📝 Plantilla de Análisis Comparativo

Crea un archivo `docs/auditorias/ANALISIS_COMPARATIVO_2026-02-17.md`:

```markdown
# Auditoría Comparativa: Pruebas vs Producción

**Fecha:** 2026-02-17  
**Operación auditable:** [id_operacion]

## PARTE 1: Vistas Existentes
- Pruebas (adminerp_copy): [número de vistas WAC/COGS]
- Producción (adminerp): [número de vistas WAC/COGS]
- ✅ Coinciden: SI / NO

## PARTE 5: P&L Margen
- Pruebas - Total Ventas: [número]
- Producción - Total Ventas: [número]
- ✅ Coinciden: SI / NO

- Pruebas - Total COGS: [número]
- Producción - Total COGS: [número]
- ✅ Coinciden: SI / NO

- Pruebas - Margen %: [número]
- Producción - Margen %: [número]
- ✅ Coinciden: SI / NO

## PARTE 6: Consumo Valorizado
- Pruebas - Costo Total: [número]
- Producción - Costo Total: [número]
- ✅ Coinciden: SI / NO

## CONCLUSIÓN:
[APROBADO] / [REQUIERE INVESTIGACIÓN]

## Notas:
[Cualquier discrepancia importante]
```

---

## 🚦 Criterios de Decisión

### Si TODO coincide perfectamente ✅

Significa:
- El ambiente de pruebas es un reflejo fiel de producción
- Es **SEGURO** aplicar índices en producción
- Puedes proceder con confianza

### Si hay diferencias pero son menores 🟡

**Ejemplos menores:**
- Número de registros diferente (OK, datos pueden ser diferentes)
- Vistas con nombres ligeramente diferentes (OK si la lógica es la misma)

**Ejemplos mayores:**
- Margen % diferente (PROBLEMA)
- COGS total diferente (PROBLEMA)
- Vistas faltantes en producción (PROBLEMA)

### Si hay diferencias críticas ❌

**NO avances.** Investiga:
1. ¿El Documento_Maestro fue aplicado en producción?
2. ¿Las vistas son diferentes entre ambientes?
3. ¿Los datos de ingresos (WAC) son diferentes?

---

## 💬 Preguntas Comunes

**P: ¿Por qué los números de comandas pueden ser diferentes?**  
R: Es normal. Pruebas y producción tienen datos diferentes (la copia es de hace unos días). Lo importante es que EL ALGORITMO funcione igual.

**P: ¿Y si encuentro una diferencia en margen %?**  
R: Es CRÍTICA. Significa que una fórmula es diferente entre ambientes. Detente e investiga.

**P: ¿Cuánto tiempo debería tardar esto?**  
R: 20-30 minutos total.

---

## ✅ Checklist Final

- [ ] Script personalizado con id_operacion correcto
- [ ] Ejecutado en adminerp_copy sin errores
- [ ] Resultado guardado en `docs/auditorias/`
- [ ] Ejecutado en adminerp sin errores
- [ ] Resultado guardado en `docs/auditorias/`
- [ ] Análisis comparativo documentado
- [ ] Sin discrepancias críticas encontradas
- [ ] Listo para aplicar índices ✅

---

**Próximo paso:** Una vez completes esta auditoría, confirma conmigo los resultados antes de aplicar los índices en producción.
