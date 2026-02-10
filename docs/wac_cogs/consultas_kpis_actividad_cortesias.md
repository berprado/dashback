# Consultas KPIs, Actividad y Cortesías

Documento técnico para onboarding. Resume la lógica y el flujo implementado para obtener KPIs operativos, métricas de frecuencia de emisión de comandas y cálculo de cortesías.

## Glosario

- **KPI** (Key Performance Indicator): indicador clave de rendimiento operativo.
- **Ticket promedio**: monto promedio de venta por comanda, calculado como `total_vendido / total_comandas`.
- **Cortesía**: comanda de tipo `CORTESIA` donde el cliente no paga (el monto se toma de `cor_subtotal_anterior`).
- **Frecuencia de emisión**: cadencia temporal entre comandas, medida en minutos entre `fecha_emision`.
- **Mediana**: valor central en un conjunto de datos ordenado, más robusto que el promedio ante outliers.
- **Actividad**: pulso operativo basado en `fecha_emision`, sin filtrar por tipo de salida ni estado.

## Convenciones y alcance

- Las consultas filtran por `id_operacion` o rango de fechas según el modo (tiempo real o histórico).
- Todas las consultas usan placeholders para parametrización segura (`:op_ini`, `:op_fin`, `:dt_ini`, `:dt_fin`).
- Los KPIs de ventas consideran solo comandas finalizadas: `tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.
- Las cortesías usan el campo `cor_subtotal_anterior` como fuente del monto (ya que `sub_total` puede ser 0 en cortesías).
- Las vistas listadas son la fuente oficial; no se deben reinterpretar campos a nivel de UI.

---

## Consulta de KPIs base del dashboard

**Objetivo**
- Obtener los indicadores operativos principales: ventas, comandas, ítems y ticket promedio.

**Campos**
- `total_vendido`: suma de `sub_total` para comandas finalizadas (tipo `VENTA`, estado `PROCESADO`, impresión `IMPRESO`).
- `total_comandas`: conteo distinto de `id_comanda` para comandas finalizadas.
- `items_vendidos`: suma de `cantidad` para comandas finalizadas.
- `ticket_promedio`: promedio de venta por comanda, calculado como `total_vendido / NULLIF(total_comandas, 0)`.

**Campos adicionales (diagnóstico de impresión)**
- `total_vendido_impreso_log`: ventas calculadas aceptando impresión confirmada vía `vw_comanda_ultima_impresion`.
- `total_comandas_impreso_log`: comandas con impresión confirmada vía log.
- `items_vendidos_impreso_log`: ítems con impresión confirmada vía log.
- `ticket_promedio_impreso_log`: ticket promedio usando log de impresión.

**Uso típico**
- Dashboard principal para toma de decisiones operativas en tiempo real.
- Comparación entre cálculo estándar y diagnóstico vía log de impresión (cuando `estado_impresion` queda `NULL` en `bar_comanda`).
- Base para análisis de tendencias y proyecciones de venta.

```sql
SELECT
    -- KPIs de ventas finalizadas (estándar)
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND v.estado_impresion = 'IMPRESO'
                    THEN v.sub_total
                ELSE 0
            END
        ),
        0
    ) AS total_vendido,
    
    COUNT(
        DISTINCT CASE
            WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
             AND v.estado_comanda = 'PROCESADO'
             AND v.estado_impresion = 'IMPRESO'
                THEN v.id_comanda
        END
    ) AS total_comandas,
    
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND v.estado_impresion = 'IMPRESO'
                    THEN v.cantidad
                ELSE 0
            END
        ),
        0
    ) AS items_vendidos,
    
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND v.estado_impresion = 'IMPRESO'
                    THEN v.sub_total
                ELSE 0
            END
        ) / NULLIF(
            COUNT(
                DISTINCT CASE
                    WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                     AND v.estado_comanda = 'PROCESADO'
                     AND v.estado_impresion = 'IMPRESO'
                        THEN v.id_comanda
                END
            ),
            0
        ),
        0
    ) AS ticket_promedio,

    -- KPIs con diagnóstico vía log de impresión (opcional)
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')
                    THEN v.sub_total
                ELSE 0
            END
        ),
        0
    ) AS total_vendido_impreso_log,
    
    COUNT(
        DISTINCT CASE
            WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
             AND v.estado_comanda = 'PROCESADO'
             AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')
                THEN v.id_comanda
        END
    ) AS total_comandas_impreso_log,
    
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')
                    THEN v.cantidad
                ELSE 0
            END
        ),
        0
    ) AS items_vendidos_impreso_log,
    
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')
                    THEN v.sub_total
                ELSE 0
            END
        ) / NULLIF(
            COUNT(
                DISTINCT CASE
                    WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'VENTA'
                     AND v.estado_comanda = 'PROCESADO'
                     AND (v.estado_impresion = 'IMPRESO' OR ei_log.nombre = 'IMPRESO')
                        THEN v.id_comanda
                END
            ),
            0
        ),
        0
    ) AS ticket_promedio_impreso_log

FROM comandas_v6 v
LEFT JOIN vw_comanda_ultima_impresion imp
    ON imp.id_comanda = v.id_comanda
LEFT JOIN parameter_table ei_log
    ON ei_log.id = imp.ind_estado_impresion
   AND ei_log.id_master = 10
   AND ei_log.estado = 'HAB'
WHERE v.id_operacion BETWEEN :op_ini AND :op_fin;
```

**Nota técnica importante**
- El cálculo estándar usa solo `v.estado_impresion = 'IMPRESO'`.
- El cálculo con diagnóstico acepta además `ei_log.nombre = 'IMPRESO'` (desde `vw_comanda_ultima_impresion`).
- Esto permite detectar comandas que se imprimieron pero cuyo `estado_impresion` quedó `NULL` en `bar_comanda`.

---

## Consulta de cortesías

**Objetivo**
- Calcular el monto y cantidad de cortesías otorgadas en la operativa.

**Campos**
- `total_cortesia`: suma de montos de cortesías finalizadas (usa `cor_subtotal_anterior` porque `sub_total` puede ser 0).
- `comandas_cortesia`: conteo distinto de comandas tipo `CORTESIA` finalizadas.
- `items_cortesia`: suma de cantidades de ítems en comandas cortesía finalizadas.

**Criterio de cortesía finalizada**
- `tipo_salida='CORTESIA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.

**Regla de negocio crítica**
- El valor monetario de una cortesía se toma del campo `cor_subtotal_anterior`, no de `sub_total`.
- Esto es porque en cortesías el `sub_total` suele estar en 0 (el cliente no pagó), pero `cor_subtotal_anterior` guarda el valor "teórico" que habría costado.

**Uso típico**
- Control de cortesías otorgadas por operativa.
- Análisis de impacto de cortesías en rentabilidad (comparar con margen bruto).
- Auditoría de autorizaciones de cortesías.

```sql
SELECT
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'CORTESIA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND v.estado_impresion = 'IMPRESO'
                    THEN COALESCE(v.cor_subtotal_anterior, v.sub_total, 0)
                ELSE 0
            END
        ),
        0
    ) AS total_cortesia,
    
    COUNT(
        DISTINCT CASE
            WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'CORTESIA'
             AND v.estado_comanda = 'PROCESADO'
             AND v.estado_impresion = 'IMPRESO'
                THEN v.id_comanda
        END
    ) AS comandas_cortesia,
    
    COALESCE(
        SUM(
            CASE
                WHEN UPPER(COALESCE(v.tipo_salida, '')) = 'CORTESIA'
                 AND v.estado_comanda = 'PROCESADO'
                 AND v.estado_impresion = 'IMPRESO'
                    THEN v.cantidad
                ELSE 0
            END
        ),
        0
    ) AS items_cortesia

FROM comandas_v6 v
WHERE v.id_operacion BETWEEN :op_ini AND :op_fin;
```

**Nota sobre `cor_subtotal_anterior`**
- Es el subtotal original antes de aplicar la cortesía.
- Se usa como proxy del "valor de mercado" de la cortesía.
- Si `cor_subtotal_anterior` es `NULL`, se usa `sub_total` como fallback (aunque probablemente sea 0).

---

## Consulta de actividad y frecuencia de emisión

**Objetivo**
- Medir el pulso operativo basándose en la frecuencia de emisión de comandas.

**Métricas calculadas**
- `last_ts`: timestamp de la última comanda emitida (MAX de `fecha_emision`).
- `minutes_since_last`: minutos transcurridos desde la última comanda hasta el momento actual.
- `recent_median_min`: mediana de minutos entre las últimas N comandas (ejemplo: últimas 10).
- `recent_intervals`: cantidad de intervalos calculados en el conjunto reciente.
- `all_median_min`: mediana de minutos entre todas las comandas del rango/operativa.
- `all_intervals`: cantidad de intervalos calculados en el conjunto completo.

**Criterio de cálculo**
- Se toma un timestamp único por comanda: `MIN(fecha_emision)` agrupado por `id_comanda`.
- Esto evita contar múltiples veces la misma comanda (la vista tiene múltiples filas por ítem).
- No se filtra por tipo de salida ni estado: se mide actividad pura (pulso operativo).

**Uso típico**
- Monitoreo de operación en tiempo real: detectar cuando la cocina se "enfría" (muchos minutos desde última comanda).
- Análisis de ritmo de trabajo: cuantos minutos en promedio pasan entre comandas.
- Comparativa de ritmo entre turnos, días, o períodos históricos.

```sql
-- Subconsulta: últimas N comandas (ordenadas DESC, luego reordenadas ASC para diff)
SELECT
    id_comanda,
    fecha_emision
FROM (
    SELECT
        id_comanda,
        MIN(fecha_emision) AS fecha_emision
    FROM comandas_v6
    WHERE id_operacion BETWEEN :op_ini AND :op_fin
    GROUP BY id_comanda
    ORDER BY fecha_emision DESC
    LIMIT 10
) t
ORDER BY fecha_emision ASC;
```

```sql
-- Consulta: todas las comandas del contexto (para ritmo global)
SELECT
    id_comanda,
    MIN(fecha_emision) AS fecha_emision
FROM comandas_v6
WHERE id_operacion BETWEEN :op_ini AND :op_fin
GROUP BY id_comanda
ORDER BY fecha_emision ASC;
```

**Proceso de cálculo (lado Python)**
1. Se obtienen timestamps de emisión por comanda (uno por `id_comanda`).
2. Se calcula el `diff()` entre timestamps consecutivos usando Pandas.
3. Se convierte a minutos (`total_seconds() / 60`).
4. Se obtiene la mediana de los intervalos (más robusta que promedio ante outliers).
5. Último timestamp se compara con el reloj actual del servidor para calcular `minutes_since_last`.

**Regla de negocio**
- Esta métrica no distingue entre ventas, cortesías o anuladas: mide **actividad** pura.
- Es útil para detectar "lagunas operativas" donde no hubo emisión de comandas.
- En tiempo real, si `minutes_since_last` es muy alto, puede indicar operación detenida o fin de jornada.

---

## Consulta de estado operativo

**Objetivo**
- Contar comandas en estados operativos clave para visibilidad de gestión.

**Campos**
- `comandas_pendientes`: comandas con `estado_comanda='PENDIENTE'`.
- `comandas_anuladas`: comandas con `estado_comanda='ANULADO'`.
- `comandas_impresion_pendiente`: comandas con `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`.
- `comandas_sin_estado_impresion`: comandas con `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`.

**Semántica de impresión**
- `estado_impresion='PENDIENTE'` es temporal (en cola/por procesar).
- `estado_impresion='IMPRESO'` significa ya procesada/impresa.
- `estado_impresion IS NULL` puede aparecer antes de imprimirse o por dato faltante.

**Uso típico**
- Monitoreo operativo en tiempo real: detectar comandas que requieren atención.
- Auditoría de flujo: identificar cuellos de botella en impresión.
- Control de calidad: validar que todas las comandas siguen el ciclo esperado.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN estado_comanda = 'PENDIENTE' THEN id_comanda END) AS comandas_pendientes,
    COUNT(DISTINCT CASE WHEN estado_comanda = 'ANULADO' THEN id_comanda END) AS comandas_anuladas,
    COUNT(
        DISTINCT CASE
            WHEN estado_comanda <> 'ANULADO' AND estado_impresion = 'PENDIENTE' THEN id_comanda
        END
    ) AS comandas_impresion_pendiente,
    COUNT(
        DISTINCT CASE
            WHEN estado_comanda <> 'ANULADO' AND estado_impresion IS NULL THEN id_comanda
        END
    ) AS comandas_sin_estado_impresion
FROM comandas_v6
WHERE id_operacion BETWEEN :op_ini AND :op_fin;
```

---

## Trazabilidad de datos (mapa de origen)

### Para KPIs y cortesías

1. Tabla/vista base: `comandas_v6` (tiempo real) o `comandas_v6_todas` (histórico)
2. Filtro por contexto: `id_operacion` o rango de fechas `fecha_emision`
3. Condiciones de finalización:
   - Ventas: `tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`
   - Cortesías: `tipo_salida='CORTESIA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`
4. Campos usados:
   - `sub_total` (para ventas)
   - `cor_subtotal_anterior` (para cortesías)
   - `cantidad` (para ítems)
   - `id_comanda` (para conteo de comandas)
5. Agregación: `SUM`, `COUNT DISTINCT`, cálculo de ticket promedio
6. Presentación en UI: métricas formateadas (Bs con miles y decimales Bolivia)

### Para actividad y frecuencia de emisión

1. Tabla/vista base: `comandas_v6` (tiempo real) o `comandas_v6_todas` (histórico)
2. Agrupación: `MIN(fecha_emision)` por `id_comanda` (un timestamp por comanda)
3. Sin filtro de tipo/estado: mide actividad pura
4. Ordenamiento: por `fecha_emision` ASC (para cálculo de intervalos)
5. Cálculo de intervalos: `diff()` de timestamps en Pandas
6. Métrica clave: mediana de minutos entre comandas (robusta ante outliers)
7. Contexto temporal: última comanda vs reloj actual

### Para estado operativo

1. Tabla/vista base: `comandas_v6` (tiempo real) o `comandas_v6_todas` (histórico)
2. Condiciones por estado:
   - Pendientes: `estado_comanda='PENDIENTE'`
   - Anuladas: `estado_comanda='ANULADO'`
   - Impresión pendiente: `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`
   - Sin estado impresión: `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`
3. Agregación: `COUNT DISTINCT` por `id_comanda`
4. Presentación en UI: contadores con opción de ver IDs (bajo demanda)

---

## Explicación del flujo end-to-end

### KPIs y cortesías

El cálculo de KPIs y cortesías sigue un pipeline directo desde la vista principal hasta la UI. Primero, se consulta la vista correspondiente (`comandas_v6` en tiempo real o `comandas_v6_todas` en histórico) aplicando filtros por `id_operacion` o rango de fechas. Luego se aplican condiciones `CASE WHEN` para clasificar cada fila según su `tipo_salida`, `estado_comanda` y `estado_impresion`.

Para ventas finalizadas, se suma `sub_total` solo cuando cumple la triple condición: tipo VENTA, estado PROCESADO e impresión IMPRESO. Para cortesías, se usa la misma lógica de finalización pero con `tipo_salida='CORTESIA'`, y el monto se toma de `cor_subtotal_anterior` (no de `sub_total`, que suele ser 0 en cortesías).

El ticket promedio se calcula dividiendo `total_vendido` entre `total_comandas`, usando `NULLIF` para evitar división por cero. Los ítems vendidos se obtienen sumando el campo `cantidad` bajo las mismas condiciones de finalización.

Opcionalmente, se puede habilitar un diagnóstico de impresión que une con `vw_comanda_ultima_impresion` para aceptar también comandas marcadas como IMPRESO en el log de impresión (útil cuando `bar_comanda.estado_impresion` queda `NULL` por alguna anomalía del sistema).

Todos estos datos se agregan en una sola consulta SQL y se exponen como diccionario Python en `src/metrics.py`, donde se convierten a tipos numéricos seguros (`float`, `int`) antes de pasarlos a la UI.

### Actividad y frecuencia de emisión

La medición de actividad sigue un enfoque diferente, centrado en timestamps de emisión. Primero, se obtiene un timestamp único por comanda mediante `MIN(fecha_emision) GROUP BY id_comanda`, evitando así contar múltiples veces la misma comanda (la vista tiene múltiples filas por ítem).

Se ejecutan dos consultas: una para las últimas N comandas (ejemplo: últimas 10) y otra para todas las comandas del contexto. Los resultados se ordenan ascendentemente por `fecha_emision` para calcular intervalos consecutivos.

En Python (usando Pandas), se calcula `diff()` entre timestamps consecutivos, se convierte a minutos y se obtiene la mediana (más robusta que el promedio ante outliers como pausas largas o cambios de turno).

El último timestamp se compara con el reloj actual del servidor Streamlit para calcular `minutes_since_last`, que indica cuántos minutos han pasado sin actividad. Esta métrica es crítica en tiempo real para detectar operación detenida o fin de jornada.

No se aplican filtros de tipo de salida ni estado: se mide **pulso operativo puro** basado solo en `fecha_emision`.

### Estado operativo

El estado operativo se calcula mediante una sola consulta agregada que usa `COUNT DISTINCT` con condiciones `CASE WHEN` para cada categoría. Se cuenta cada `id_comanda` una sola vez, clasificándola según su `estado_comanda` y `estado_impresion`.

Comandas pendientes son aquellas con `estado_comanda='PENDIENTE'`. Comandas anuladas tienen `estado_comanda='ANULADO'`. Las categorías de impresión (pendiente y sin estado) filtran primero por `estado_comanda<>'ANULADO'` para no contar anuladas dos veces.

`estado_impresion='PENDIENTE'` indica comandas en cola de impresión (temporal). `estado_impresion IS NULL` puede significar comandas aún no procesadas o datos faltantes. La UI permite expandir estas métricas para ver los IDs específicos (con límite configurable).

Este diseño en capas permite auditar y diagnosticar problemas en cualquier nivel. Si un KPI parece incorrecto, se puede rastrear hacia atrás: revisar la consulta SQL en `query_store.py`, verificar los filtros aplicados, inspeccionar el detalle de comandas, y finalmente validar contra la tabla `bar_comanda` o el log de impresión. Cada capa tiene un propósito específico y se puede testear de forma independiente.
