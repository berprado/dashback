
# Skill: MySQL (Dashback)

## Objetivo
Definir lineamientos prácticos para escribir, depurar y optimizar consultas **MySQL 5.6.x** para el dashboard Dashback (Streamlit) **sin romper producción**.

Esta skill se enfoca en:
- Consultas **solo lectura** (SELECT).
- Uso de **vistas** del dashboard como fuente principal.
- Parametrización correcta (evitar SQL injection y problemas de compatibilidad).
- Diagnóstico de discrepancias (p.ej. `estado_impresion` vs tablas base/logs).

---

## Contexto del proyecto (muy importante)
- Fuente real-time: vista `comandas_v6`.
- Fuente histórico: vista `comandas_v6_todas` (y/o `comandas_v6_base` según disponibilidad).
- Filtros estándar del dashboard:
	- Por operativas: `id_operacion BETWEEN :op_ini AND :op_fin`
	- Por fechas: `fecha_emision BETWEEN :dt_ini AND :dt_fin`
- Tablas útiles para diagnóstico:
	- `bar_comanda` (estado/impresión persistida)
	- `bar_comanda_impresion` (log)
	- `vw_comanda_ultima_impresion` (último estado del log)
	- `parameter_table` (catálogos, validar `id_master` y `estado='HAB'`)

---

## Reglas de seguridad y operación
1) **Read-only**: no generar `INSERT/UPDATE/DELETE/DDL`.
2) **Evitar locks pesados** en producción:
	 - Evitar `SHOW CREATE VIEW`/`ALTER VIEW`/`CREATE VIEW` en ventanas de operación.
	 - Preferir consultas de verificación acotadas con `WHERE` + `LIMIT`.
3) **No hardcodear esquema** (`adminerp.` / `adminerp_copy.`): usar nombres no calificados.
4) **Siempre limitar** cuando se inspecciona detalle:
	 - `ORDER BY ... DESC` + `LIMIT 50/100/500`.
5) **No asumir que NULL = PENDIENTE**:
	 - `estado_impresion IS NULL` es una señal distinta (dato no persistido / incompleto).
6) **Validar catálogos**:
	 - Cuando se join-ea `parameter_table`, filtrar por `id_master` correcto y `estado='HAB'`.

---

## Parametrización (obligatorio)
En este repo, el patrón recomendado es **placeholders estilo SQLAlchemy**:
- Usar `:param` (ej: `:op_ini`, `:op_fin`, `:dt_ini`, `:dt_fin`).
- No interpolar strings de usuario dentro del SQL.

Nota:
- La capa de ejecución del proyecto ya convierte `:param` a `%(param)s` cuando corresponde.

---

## Patrones recomendados (consultas típicas)

### 1) Conteos operativos por estado
```sql
SELECT
	COUNT(DISTINCT CASE WHEN estado_comanda = 'PENDIENTE' THEN id_comanda END) AS comandas_pendientes,
	COUNT(DISTINCT CASE WHEN estado_comanda = 'ANULADO' THEN id_comanda END)   AS comandas_anuladas,
	COUNT(DISTINCT CASE WHEN estado_comanda <> 'ANULADO' AND estado_impresion = 'PENDIENTE' THEN id_comanda END)
		AS impresion_pendiente,
	COUNT(DISTINCT CASE WHEN estado_comanda <> 'ANULADO' AND estado_impresion IS NULL THEN id_comanda END)
		AS sin_estado_impresion
FROM comandas_v6
WHERE id_operacion = :op;
```

### 2) Traer IDs para inspección (últimos)
```sql
SELECT DISTINCT id_comanda
FROM comandas_v6
WHERE id_operacion = :op
	AND estado_comanda <> 'ANULADO'
	AND estado_impresion IS NULL
ORDER BY id_comanda DESC
LIMIT 50;
```

### 3) Diagnóstico “vista vs bar_comanda vs log”
Útil cuando el dashboard muestra `NULL` pero se imprimió físicamente.

```sql
SELECT
	t.id_comanda,
	t.id_operacion,
	t.fecha_emision_ult,
	t.estado_impresion AS estado_impresion_vista,

	bc.estado_impresion AS estado_impresion_id_bar_comanda,
	pti.nombre AS estado_impresion_bar_comanda,

	vui.ind_estado_impresion AS estado_impresion_id_log,
	pti2.nombre AS estado_impresion_log
FROM (
	SELECT
		id_comanda,
		MAX(id_operacion) AS id_operacion,
		MAX(fecha_emision) AS fecha_emision_ult,
		MAX(estado_impresion) AS estado_impresion
	FROM comandas_v6
	WHERE id_comanda IN (/* lista de enteros */)
	GROUP BY id_comanda
) t
LEFT JOIN bar_comanda bc
	ON bc.id = t.id_comanda
LEFT JOIN parameter_table pti
	ON pti.id = bc.estado_impresion
 AND pti.id_master = 10
 AND pti.estado = 'HAB'
LEFT JOIN vw_comanda_ultima_impresion vui
	ON vui.id_comanda = t.id_comanda
LEFT JOIN parameter_table pti2
	ON pti2.id = vui.ind_estado_impresion
 AND pti2.id_master = 10
 AND pti2.estado = 'HAB'
ORDER BY t.id_comanda DESC;
```

Interpretación rápida:
- Todo `NULL` (vista + bar_comanda + log) ⇒ el POS **aún no persistió** estado.
- `vista=NULL` pero `log=IMPRESO` ⇒ la vista no está reflejando el log (o estás en otra vista/base).
- `bar_comanda=IMPRESO` y `log=IMPRESO` ⇒ persistencia OK.

---

## Performance y calidad
- Preferir agregaciones sobre `COUNT(DISTINCT id_comanda)` en vez de contar filas de ítems.
- Para cadencia/actividad por comanda, usar **una fila por comanda**:
	- `MIN(fecha_emision)` por `id_comanda` (y luego ordenar/limitar).
- Evitar `ORDER BY` sin `LIMIT` en vistas grandes.

---

## Checklist antes de “dar por válido” un resultado
- ¿Estoy consultando la **misma DB** que el dashboard (`DATABASE()`)?
- ¿Estoy en la vista correcta (real-time `comandas_v6` vs histórico `comandas_v6_todas`)?
- ¿La consulta respeta el filtro estándar (`id_operacion` o `fecha_emision`)?
- ¿Los joins a `parameter_table` filtran `id_master` y `estado='HAB'`?
- ¿Hay `LIMIT` si es inspección de detalle?

---

## Cómo integrar en el código (cuando aplique)
- Definir SQL en `src/query_store.py` como función `q_...()`.
- Ejecutar desde `src/metrics.py` usando `_run_df(...)`.
- En UI, ejecutar bajo demanda (checkbox/botón) si es una consulta pesada.

