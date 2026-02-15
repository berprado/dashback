# 📊 Guía técnica por etapas — Dashboard Operativo Backstage (Streamlit + MySQL 5.6)

> **Objetivo:** Determinar la información que se debe mostrar como vista principal al momento de iniciar la aplicación.  
> **Alcance:** dashboard **tiempo real** (operativa activa) + **histórico** (rango de operativas y/o fechas) usando vistas SQL basadas en `bar_comanda`, `bar_detalle_comanda_salida`, `ope_operacion`, `parameter_table`, etc.

---

Documentos de referencia:
- `docs/01-flujo_inicio_dashboard.md` (lógica de arranque y casos límite)
- `docs/02-guia_dashboard_backstage.md` (guía técnica y definición de vistas)
- `docs/analisis_wac_cogs_margenes.md` (WAC/COGS/márgenes + mejoras propuestas)
- `docs/playbook_performance_mysql56.md` (performance MySQL 5.6.12: EXPLAIN + índices mínimos)

## Estado de implementación (en este repo)

Esta guía mezcla 2 cosas:

- ✅ **Implementado en el código** (lo que hoy corre en el repo):
  - Conexión vía **Streamlit Connections** (`.streamlit/secrets.toml`)
  - Arranque **tiempo real vs histórico** (selección de vista y defaults)
  - Filtros básicos con `Filters` + `build_where` (por operativas o fechas)
  - KPIs, cortesías, estado operativo, gráficos, detalle bajo demanda
  - Bloque **Actividad** (última comanda / minutos desde la última / ritmo)
- 🟡 **Guía/Referencia o Futuro** (no necesariamente implementado tal cual):
  - Ejemplos de engine SQLAlchemy “manual” (`create_engine`) y `pd.read_sql`
  - Prefacturación (`q_prefacturacion`) y otros bloques mencionados como ideas

Cuando haya dudas, la fuente de verdad es el código en `src/`.

Cómo leer esta guía (para evitar confusiones):
- ✅ “Implementado” significa que existe en el repo y se usa en el flujo actual.
- 🟡 “Referencia/Futuro” significa que puede servir como guía, pero no está cableado tal cual.
- Los ejemplos de SQL DDL (CREATE VIEW) describen la preparación de vistas en MySQL; la app asume que esas vistas ya existen en la DB activa.

## 0) Requisitos y supuestos

### Tecnologías
- **Python 3.10+**
- **Streamlit 1.52.2**
- **MySQL 5.6.12**
- Driver MySQL (recomendado): `mysql-connector-python`
- SQLAlchemy (requerido por Streamlit Connections para el `url`)
- Pandas para lectura y agregación

### Nota de entornos (Local vs Producción)
- Las vistas pueden vivir en esquemas distintos (p.ej. `adminerp_copy` en local y `adminerp` en producción).
- En el código Python, evitar hardcodear el esquema: usar nombres no calificados (ej. `comandas_v6`) y depender de la DB definida en la URL.

### Convenciones de negocio (importantes)
- `bar_comanda.estado` es el **estado lógico** del registro (`HAB` / `DES`).  
  ✅ El dashboard debe **mostrar solo `HAB`**.
- `ope_operacion.estado` también es lógico (`HAB` / `DES`).  
  ✅ El dashboard debe **mostrar solo `HAB`**.
- Estados de negocio se obtienen de `parameter_table`:
  - `parameter_table.id_master` referencia el catálogo en `master_table.id`.
    - La descripción/definición del catálogo está en `master_table.descripcion`.
    - Útil para auditorías rápidas (¿qué significa cada `id_master`?):

```sql
SELECT mt.id, mt.descripcion
FROM master_table mt
WHERE mt.id IN (6, 7, 10, 15);
```

  - `estado_operacion` → `id_master = 6` (22 EN PROCESO, 23 CERRADO, 24 INICIO CIERRE)
  - `estado_comanda` → `id_master = 7` (25 PENDIENTE, 26 PROCESADO, 27 ANULADO)
  - `estado_impresion` → `id_master = 10` (31 IMPRESO, 32 PENDIENTE)
  - `tipo_salida_comanda` → `id_master = 15` (50 VENTA, 51 CORTESIA)

---

### Semántica adicional: `estado_impresion` en la práctica
- `IMPRESO`: impresión ya procesada.
- `PENDIENTE`: estado temporal (en cola/por procesar).
- `NULL`: puede indicar que aún no fue procesada/impresa; también aparece en comandas **anuladas**.

Nota importante (caso real observado):
- Puede ocurrir que la **impresión física** suceda, pero `bar_comanda.estado_impresion` quede `NULL` por un tiempo.
- En esos casos, `comandas_v6` reflejará `NULL` (porque depende de `bar_comanda`), pero el log
  `vw_comanda_ultima_impresion` / `bar_comanda_impresion` puede ya indicar `IMPRESO`.
- La vista `comandas_v7` está construida desde el log (`vw_comanda_ultima_impresion`) y tiende a mostrar un estado
  “efectivo” (por ejemplo, `IMPRESO` aun cuando `bar_comanda.estado_impresion` es `NULL`).

Nota sobre este repo:
- La app **no** consulta `comandas_v7` para los KPIs/gráficos.
- El toggle “Ventas: usar log de impresión” mantiene la vista `comandas_v6`/`comandas_v6_todas` como fuente y
  aplica una **señal alternativa** vía `vw_comanda_ultima_impresion` (join en las queries).
- `comandas_v7` se valida en el healthcheck por si existe en la DB, pero no es un requisito funcional del código.

Por eso, en la UI existe un expander de diagnóstico para comparar “Ventas finalizadas estrictas” vs “Ventas con log”.

Regla práctica:
- Para identificar anuladas, usar `estado_comanda='ANULADO'` (suele venir con `estado_impresion=NULL`).
- Para identificar pendientes de impresión, usar `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`.
- Para identificar “sin estado de impresión”, usar `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`.

---

## Estándar de ayudas (tooltips `help`) en la UI

Para evitar ambigüedades (especialmente entre “ventas”, “actividad” y “estado operativo”), las ayudas (`help=`) deben seguir este estándar:

- Definir **qué mide** el KPI (regla de negocio, en una frase).
- Indicar **qué incluye/excluye** (p.ej. “ventas finalizadas” vs “actividad sin filtrar por tipo/estado”).
- Aclarar el **contexto**: vista + filtros activos del modo actual (tiempo real / histórico).

Reglas clave que deben aparecer explícitas cuando aplique:
- Ventas: `tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.
- Cortesías: `tipo_salida='CORTESIA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.
- Impresión pendiente: `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`.
- Sin estado impresión: `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`.

## 0.1) Vista financiera (P&L): `vw_margen_comanda`

Para el bloque ejecutivo de Márgenes & Rentabilidad se usa la vista `vw_margen_comanda`.

Requisitos mínimos esperados:
- `total_venta`: venta total por comanda (solo ventas reales, sin cortesías).
- `cogs_comanda`: costo total de insumos consumidos.
- `margen_comanda`: utilidad bruta por comanda.
- `id_operacion` (y `fecha_emision` si se habilita filtro por fechas).

La consulta consolidada suma esos campos y calcula `margen_pct = (margen / ventas) * 100`.

Detalle por comanda:
- Fuente: `vw_margen_comanda`.
- Campos esperados: `id_operacion`, `id_comanda`, `id_barra`, `total_venta`, `cogs_comanda`, `margen_comanda`.
- Se ordena por `id_comanda DESC` y se aplica un límite configurable desde la UI.

Consumo valorizado:
- Fuente: `vw_consumo_valorizado_operativa`.
- Campos esperados: `id_operacion`, `id_producto`, `cantidad_consumida_base`, `wac_operativa`, `costo_consumo`.
- Se ordena por `costo_consumo DESC` y se aplica un límite configurable desde la UI.
- Útil para conciliación de inventario, detección de mermas y análisis de costos.

Consumo sin valorar:
- Fuente: `vw_consumo_insumos_operativa`.
- Campos esperados: `id_operacion`, `id_producto`, `cantidad_consumida_base`.
- Se ordena por `cantidad_consumida_base DESC` y se aplica un límite configurable desde la UI.
- Sanidad de cantidades: aísla problemas de receta/multiplicación/unidades de problemas de WAC/margen.

COGS por comanda:
- Fuente: `vw_cogs_comanda`.
- Campos esperados: `id_operacion`, `id_comanda`, `id_barra`, `cogs_comanda`.
- Se ordena por `cogs_comanda DESC` y se aplica un límite configurable desde la UI.
- Ver solo el costo, sin precio de venta: ideal para cortesías y auditoría de consumo puro.

## 1) Etapa 1 — Preparar las vistas SQL (fuente de verdad)

### 1.1 Vista base recomendada: `comandas_v6_base`
**Motivo:** evitar duplicar lógica en múltiples vistas; todo parte de una sola vista “base” (histórica) con filtros de validez.

✅ Incluye:
- joins a `ope_operacion` para exponer `estado_operacion`
- joins a `parameter_table` para nombres amigables
- filtros: `bar_comanda.estado='HAB'` y `ope_operacion.estado='HAB'`

> Ejecutar en MySQL:

> Nota: los ejemplos de esta sección usan `adminerp_copy` como referencia. En el dashboard (Python) se usan nombres no calificados (ej. `comandas_v6`) y el esquema real lo define la DB activa en la URL de conexión.

```sql
CREATE
  DEFINER = 'root'@'localhost'
VIEW adminerp_copy.comandas_v6_base
AS
SELECT
  dcs.id                               AS id,
  dcs.cantidad                         AS cantidad,
  dcs.id_comanda                       AS id_comanda,
  p.codigo                             AS id_producto,
  dcs.id_salida_combo_coctel           AS id_salida_combo_coctel,
  cc.codigo                            AS id_bar_combo_coctel,
  dcs.precio_venta                     AS precio_venta,
  dcs.sub_total                        AS sub_total,
  dcs.producto_coctel                  AS producto_coctel,
  dcs.cor_subtotal_anterior            AS cor_subtotal_anterior,

  c.id_barra                           AS id_barra,
  c.usuario_reg                        AS usuario_reg,
  c.fecha                              AS fecha_emision,
  dcs.fecha_mod                        AS fecha_mod,

  c.estado                             AS estado,              -- HAB/DES (comanda)
  c.id_operacion                       AS id_operacion,
  c.id_mesa                            AS id_mesa,
  c.razon_social                       AS razon_social,
  c.nit                                AS nit,
  c.id_factura                         AS id_factura,
  c.nro_factura                        AS nro_factura,

  -- Normalización producto/combos
  COALESCE(p.nombre, cc.nombre)        AS nombre,
  COALESCE(p.descripcion, cc.descripcion) AS descripcion,
  COALESCE(p.codigo, cc.codigo)        AS id_producto_combo,

  -- Estados “de negocio” (user friendly)
  ts.nombre                            AS tipo_salida,
  ec.nombre                            AS estado_comanda,
  ei.nombre                            AS estado_impresion,
  COALESCE(catp.nombre, catc.nombre)   AS categoria,

  -- Operación
  op.estado_operacion                  AS estado_operacion_id,
  eop.nombre                           AS estado_operacion
FROM bar_detalle_comanda_salida dcs
JOIN bar_comanda c
  ON dcs.id_comanda = c.id
JOIN ope_operacion op
  ON op.id = c.id_operacion

LEFT JOIN alm_producto p
  ON dcs.id_producto = p.id
LEFT JOIN bar_combo_coctel cc
  ON dcs.id_bar_combo_coctel = cc.id
LEFT JOIN alm_categoria catp
  ON p.id_categoria = catp.id
LEFT JOIN alm_categoria catc
  ON cc.id_categoria = catc.id

LEFT JOIN parameter_table ts
  ON c.tipo_salida = ts.id
 AND ts.id_master = 15
 AND ts.estado = 'HAB'
LEFT JOIN parameter_table ec
  ON c.estado_comanda = ec.id
 AND ec.id_master = 7
 AND ec.estado = 'HAB'
LEFT JOIN parameter_table ei
  ON c.estado_impresion = ei.id
 AND ei.id_master = 10
 AND ei.estado = 'HAB'
LEFT JOIN parameter_table eop
  ON op.estado_operacion = eop.id
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE
  c.estado = 'HAB'
  AND op.estado = 'HAB';
```

### 1.2 Vista histórica: `comandas_v6_todas`
```sql
CREATE
  DEFINER = 'root'@'localhost'
VIEW adminerp_copy.comandas_v6_todas
AS
SELECT * FROM adminerp_copy.comandas_v6_base;
```

### 1.3 Vista tiempo real: `comandas_v6` (operativa activa)
**Definición:** última operativa con estado 22 (EN PROCESO) o 24 (INICIO CIERRE).

```sql
CREATE
  DEFINER = 'root'@'localhost'
VIEW adminerp_copy.comandas_v6
AS
SELECT *
FROM adminerp_copy.comandas_v6_base
WHERE id_operacion = (
  SELECT op2.id
  FROM ope_operacion op2
  WHERE op2.estado='HAB'
    AND op2.estado_operacion IN (22, 24)
  ORDER BY op2.id DESC
  LIMIT 1
);
```

---

## 2) Etapa 2 — Estructura del proyecto (recomendada)

```
dashboard/
  app.py
  requirements.txt
  .streamlit/
    secrets.toml
  src/
    db.py
    query_store.py
    metrics.py
    ui/
      layout.py
      components.py
```

---

## 3) Etapa 3 — Capa de queries “redonda” (sin copy-paste)

### 3.1 Objetivo
- Centralizar SQL en un solo lugar
- Reusar la misma lógica de filtros para **tiempo real** y **histórico**
- Minimizar errores por “filtro olvidado”

### 3.2 `query_store.py` (patrón del repo)

✅ Nota: la implementación real vive en `src/query_store.py` (queries + `fetch_dataframe`).
Los snippets de esta sección son un resumen para lectura rápida; si vas a modificar lógica, edita directamente el archivo.

En este proyecto se usa **Streamlit Connections**, por lo que la parametrización recomendada es estilo SQLAlchemy: `:param`.

Nota importante sobre consistencia:
- La clase `Filters` implementada hoy en el repo contiene **solo** rangos por operativa o fechas (`op_ini/op_fin`, `dt_ini/dt_fin`).
- Otros filtros por dimensión (barra/categoría/usuario/estado/tipo) son ideas posibles, pero **no están implementados** en el código actual.

```python
# src/query_store.py (resumen fiel al repo)
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Filters:
    op_ini: int | None = None
    op_fin: int | None = None
    dt_ini: str | None = None  # 'YYYY-MM-DD HH:MM:SS'
    dt_fin: str | None = None


def build_where(
    filters: Filters,
    mode: str,
    *,
    table_alias: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Construye WHERE + params.

  mode:
    - 'ops'   -> filtra por id_operacion BETWEEN
    - 'dates' -> filtra por fecha_emision BETWEEN
    - 'none'  -> sin rango (tiempo real; la vista ya viene acotada)
  """

    clauses: list[str] = []
    params: dict[str, Any] = {}

    def _col(name: str) -> str:
        return f"{table_alias}.{name}" if table_alias else name

    if mode == "ops":
        if filters.op_ini is None or filters.op_fin is None:
            raise ValueError("mode='ops' requiere op_ini y op_fin")
        clauses.append(f"{_col('id_operacion')} BETWEEN :op_ini AND :op_fin")
        params["op_ini"] = int(filters.op_ini)
        params["op_fin"] = int(filters.op_fin)

    elif mode == "dates":
        if filters.dt_ini is None or filters.dt_fin is None:
            raise ValueError("mode='dates' requiere dt_ini y dt_fin")
        clauses.append(f"{_col('fecha_emision')} BETWEEN :dt_ini AND :dt_fin")
        params["dt_ini"] = filters.dt_ini
        params["dt_fin"] = filters.dt_fin

    elif mode == "none":
        pass
    else:
        raise ValueError("mode inválido: use 'ops'|'dates'|'none'")

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    return where_sql, params
```

Qué viviría en `src/query_store.py` además de `build_where`:
- Queries por bloque (`q_kpis`, `q_ventas_por_hora`, `q_por_categoria`, `q_top_productos`, `q_por_usuario`, `q_detalle`).
- Helpers de condiciones de negocio (ventas/cortesías finalizadas).
- Diagnóstico de impresión (`q_impresion_snapshot`) y señal alternativa de IMPRESO vía join a `vw_comanda_ultima_impresion`.

### 3.3 `db.py` (helper mínimo)

✅ En este repo, `src/db.py` usa `st.connection(..., type="sql")` (Streamlit Connections).
El ejemplo con `create_engine` es 🟡 **alternativo** y solo aplica si se decide no usar Connections.

```python
# src/db.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["mysql_prod"]["url"]
    return create_engine(url)

def read_df(sql: str, params: dict):
    eng = get_engine()
    return pd.read_sql(sql, eng, params=params)
```

### 3.4 `metrics.py` (capa de servicio)

✅ En este repo, la capa de servicio real está en `src/metrics.py` y expone funciones
granulares (por bloque) en vez de un `get_dashboard_data` único.

Punto clave: la UI llama a `src/metrics.py`, que a su vez genera SQL con `src/query_store.py` y ejecuta con `fetch_dataframe`.
Ejemplos reales de funciones (ver archivo): `get_kpis(...)`, `get_estado_operativo(...)`, `get_ventas_por_hora(...)`.

---

## 4) Etapa 4 — Implementación Streamlit (layout por secciones)

### 4.1 Modos de operación
- **Tiempo real:** vista `comandas_v6` con `mode='none'`
- **Histórico por operativas:** vista `comandas_v6_todas` con `mode='ops'`
- **Histórico por fechas:** vista `comandas_v6_todas` con `mode='dates'`

### 4.2 Orden recomendado del layout
1. Filtros (sidebar o top)
2. KPIs
3. Actividad (última comanda / minutos desde última / ritmo de emisión)
4. Cortesías (KPIs)
5. Estado operativo (comandas + impresión) + IDs bajo demanda
6. Gráficos en 2 columnas:
  - Ventas por hora (línea con promedio opcional) | Ventas por categoría (barras o torta)
  - Top productos (límite configurable)   | Ventas por usuario (límite configurable)
  - Badge de contexto: muestra filtros aplicados y estado del toggle de impresión
  - Tooltips enriquecidos: cada gráfico muestra datos adicionales en hover
  - Exportación: botón CSV en cada gráfico
7. Tabla detalle bajo demanda

Nota de formato (implementación actual):
- Para consistencia Bolivia, los montos se muestran como `Bs 1.100,33`.
- En la tabla de detalle, las columnas monetarias pueden renderizarse como texto ya formateado; si se ordena por ellas, el orden puede ser **lexicográfico** (texto) y no numérico.

Nota de estados (implementación actual):
- Se separa en 2 KPIs/IDs:
  - Impresión pendiente: `estado_comanda<>'ANULADO' AND estado_impresion='PENDIENTE'`.
  - Sin estado impresión: `estado_comanda<>'ANULADO' AND estado_impresion IS NULL`.
- Las anuladas se identifican por `estado_comanda='ANULADO'`.

Definición de “Ventas” (implementación actual):
- Para KPIs y gráficos de ventas, se consideran solo comandas finalizadas:
  `tipo_salida='VENTA' AND estado_comanda='PROCESADO' AND estado_impresion='IMPRESO'`.

Opción operativa (implementación actual, toggle en UI):
- Existe un checkbox “Ventas: usar log de impresión”.
- Cuando está activo, se acepta `IMPRESO` si la vista lo marca como `IMPRESO` **o** si el log
  (`vw_comanda_ultima_impresion`) indica `IMPRESO`.
- Útil cuando `bar_comanda.estado_impresion` queda `NULL` aunque la impresión física ya ocurrió.

### 4.3 Controles de rendimiento
- No cargar detalle si el usuario no lo solicita (tabs/expander).
- No cargar IDs (pendientes/impresión pendiente/sin estado/anuladas) si el usuario no lo solicita.
- Para tiempo real: refresco manual (botón “Actualizar”).

### 4.4 Presentación de métricas
- Para un look tipo dashboard, usar `st.metric(..., border=True)`.

Formato Bolivia (implementación actual):
- Centralizar el formateo en `src/ui/formatting.py`.
- Dinero: `Bs 1.100,33` (miles con punto, decimales con coma)
- Conteos: `1.100`

---

## 5) Etapa 5 — Verificación y pruebas (checklist)

### 5.1 Consistencia
- `SUM(sub_total)` del KPI = suma de la tabla detalle filtrada.
- `COUNT(DISTINCT id_comanda)` coincide con tickets mostrados.
- Pendientes de impresión: validar contra `bar_comanda.estado_impresion`.

### 5.2 Casos límite
- No hay operativa activa (vista `comandas_v6` vacía).
- Operativa activa sin ventas.
- Comandas `DES`: deben desaparecer.
- Operativas `DES`: deben desaparecer.

---

## Checklist de documentación (para mantenerla siempre al día)

Usa esta lista cada vez que cambies SQL/servicios/UI:

- Si cambias SQL en `src/query_store.py`:
  - Actualiza este doc si cambian reglas de negocio (ventas/cortesías/impresión) o si se agregan nuevas vistas requeridas.
  - Verifica que el healthcheck (`Q_HEALTHCHECK`) siga alineado con los objetos que realmente se usan.
- Si cambias servicios en `src/metrics.py`:
  - Revisa que `README.md` refleje nuevos bloques (KPIs/gráficos/diagnósticos) o cambios en definiciones.
  - Actualiza `docs/03-evolucion_y_mejoras.md` con un resumen del cambio.
- Si cambias UI en `app.py` o `src/ui/*`:
  - Asegura que los `help=` (tooltips) sigan el estándar: qué mide, incluye/excluye, contexto (vista+filtros).
  - Si agregas toggles (p.ej. “usar log de impresión”), documenta la semántica exacta y la fuente de datos.
- Si cambias dependencias:
  - Mantén `requirements.txt` sincronizado con la `.venv` (especialmente `streamlit`).
  - Actualiza la sección “Requisitos” en `README.md`.

- Consistencia de finales de línea (Windows/macOS/Linux):
  - El repo usa `.gitattributes` para normalizar a LF los archivos de código/docs.
  - Si ves warnings LF/CRLF, ejecuta `git add --renormalize .` y revisa `git status` antes de commitear.

---

## 6) Etapa 6 — Optimización futura (si el histórico crece)

**Fase 2 (opcional):** tabla de agregados al cerrar operativa (`estado_operacion=23`):
- por hora, categoría, usuario, tipo_salida, etc.

---

## Apéndice A — Query para listar operativas (selector UI)
```sql
SELECT
  op.id,
  op.fecha,
  op.nombre_operacion,
  op.estado_operacion,
  eop.nombre AS estado_operacion_nombre
FROM ope_operacion op
LEFT JOIN parameter_table eop
  ON eop.id = op.estado_operacion
 AND eop.id_master = 6
 AND eop.estado = 'HAB'
WHERE op.estado = 'HAB'
ORDER BY op.id DESC
LIMIT 200;
```

---

## Apéndice B — Por qué esta arquitectura funciona
- Una vista base evita duplicar lógica.
- Misma capa de filtros para real-time e histórico.
- Queries agregadas (rápidas) + detalle bajo demanda.
- Mantenimiento: se edita en un solo lugar.

✅ **Fin de guía.**
