# 📊 Guía técnica por etapas — Dashboard Operativo Backstage (Streamlit + MySQL 5.6)

> **Objetivo:** Determinar la informacion que se debe mostrar como vista principal al momento de iniciar la aplicacion.  
> **Alcance:** dashboard **tiempo real** (operativa activa) + **histórico** (rango de operativas y/o fechas) usando vistas SQL basadas en `bar_comanda`, `bar_detalle_comanda_salida`, `ope_operacion`, `parameter_table`, etc.

---

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
  - `estado_operacion` → `id_master = 6` (22 EN PROCESO, 23 CERRADO, 24 INICIO CIERRE)
  - `estado_comanda` → `id_master = 7` (25 PENDIENTE, 26 PROCESADO, 27 ANULADO)
  - `estado_impresion` → `id_master = 10` (31 IMPRESO, 32 PENDIENTE)
  - `tipo_salida_comanda` → `id_master = 15` (50 VENTA, 51 CORTESIA)

---

## 1) Etapa 1 — Preparar las vistas SQL (fuente de verdad)

### 1.1 Vista base recomendada: `comandas_v6_base`
**Motivo:** evitar duplicar lógica en múltiples vistas; todo parte de una sola vista “base” (histórica) con filtros de validez.

✅ Incluye:
- joins a `ope_operacion` para exponer `estado_operacion`
- joins a `parameter_table` para nombres amigables
- filtros: `bar_comanda.estado='HAB'` y `ope_operacion.estado='HAB'`

> Ejecutar en MySQL:

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
Los snippets de esta sección son de referencia y pueden simplificar/omitir partes.

En este proyecto se usa **Streamlit Connections**, por lo que la parametrización recomendada es estilo SQLAlchemy: `:param`.

```python
# src/query_store.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any, List

@dataclass(frozen=True)
class Filters:
    # Rangos
    op_ini: Optional[int] = None
    op_fin: Optional[int] = None
    dt_ini: Optional[str] = None   # 'YYYY-MM-DD HH:MM:SS'
    dt_fin: Optional[str] = None

    # Dimensiones
    id_barra: Optional[int] = None
    categoria: Optional[str] = None
    usuario: Optional[str] = None

    # Estados de negocio (ya vienen “humanizados” en la vista)
    estado_comanda: Optional[str] = None      # 'PENDIENTE'/'PROCESADO'/'ANULADO'
    estado_impresion: Optional[str] = None    # 'IMPRESO'/'PENDIENTE'/None
    tipo_salida: Optional[str] = None         # 'VENTA'/'CORTESIA'

def build_where(f: Filters, mode: str) -> Tuple[str, Dict[str, Any]]:
    """
    mode:
      - 'ops'   -> filtra por id_operacion BETWEEN
      - 'dates' -> filtra por fecha_emision BETWEEN
      - 'none'  -> sin rango (solo tiempo real, porque la vista ya está acotada)
    """
    clauses: List[str] = []
    params: Dict[str, Any] = {}

    if mode == "ops":
        if f.op_ini is None or f.op_fin is None:
            raise ValueError("mode='ops' requiere op_ini y op_fin")
      clauses.append("id_operacion BETWEEN :op_ini AND :op_fin")
      params["op_ini"] = int(f.op_ini)
      params["op_fin"] = int(f.op_fin)

    elif mode == "dates":
        if f.dt_ini is None or f.dt_fin is None:
            raise ValueError("mode='dates' requiere dt_ini y dt_fin")
      clauses.append("fecha_emision BETWEEN :dt_ini AND :dt_fin")
        params["dt_ini"] = f.dt_ini
        params["dt_fin"] = f.dt_fin

    elif mode == "none":
        pass
    else:
        raise ValueError("mode inválido: use 'ops'|'dates'|'none'")

    # Nota: el repo hoy utiliza principalmente filtros por operativa o por fechas.

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    return where_sql, params


def q_kpis(view_name: str, where_sql: str) -> str:
    return f"""
    SELECT
      SUM(sub_total) AS total_vendido,
      COUNT(DISTINCT id_comanda) AS total_comandas,
      SUM(cantidad) AS items_vendidos,
      ROUND(SUM(sub_total) / NULLIF(COUNT(DISTINCT id_comanda), 0), 2) AS ticket_promedio,

      COUNT(DISTINCT CASE WHEN estado_comanda = 'PENDIENTE' THEN id_comanda END) AS comandas_pendientes,
      COUNT(DISTINCT CASE WHEN (estado_impresion IS NULL OR estado_impresion <> 'IMPRESO') THEN id_comanda END) AS comandas_no_impresas,

      SUM(CASE WHEN tipo_salida = 'CORTESIA' THEN COALESCE(cor_subtotal_anterior, sub_total, 0) ELSE 0 END) AS monto_cortesia,
      COUNT(DISTINCT CASE WHEN tipo_salida = 'CORTESIA' THEN id_comanda END) AS comandas_cortesia,

      SUM(CASE WHEN estado_comanda = 'ANULADO' THEN sub_total ELSE 0 END) AS monto_anulado,
      COUNT(DISTINCT CASE WHEN estado_comanda = 'ANULADO' THEN id_comanda END) AS comandas_anuladas
    FROM {view_name}
    {where_sql};
    """

def q_ventas_por_hora(view_name: str, where_sql: str) -> str:
    return f"""
    SELECT
      HOUR(fecha_emision) AS hora,
      SUM(sub_total) AS total_vendido,
      COUNT(DISTINCT id_comanda) AS comandas,
      SUM(cantidad) AS items
    FROM {view_name}
    {where_sql}
    GROUP BY HOUR(fecha_emision)
    ORDER BY hora;
    """

def q_por_categoria(view_name: str, where_sql: str) -> str:
    return f"""
    SELECT
      COALESCE(categoria, 'SIN CATEGORIA') AS categoria,
      SUM(sub_total) AS total_vendido,
      SUM(cantidad)  AS unidades,
      COUNT(DISTINCT id_comanda) AS comandas,
      ROUND(SUM(sub_total) / NULLIF(COUNT(DISTINCT id_comanda), 0), 2) AS ticket_promedio
    FROM {view_name}
    {where_sql}
    GROUP BY COALESCE(categoria, 'SIN CATEGORIA')
    ORDER BY total_vendido DESC;
    """

def q_top_productos(view_name: str, where_sql: str, limit: int = 20, order_by: str = "total_vendido") -> str:
    order_expr = "total_vendido DESC"
    if order_by == "unidades":
        order_expr = "unidades DESC"

    return f"""
    SELECT
      id_producto_combo,
      nombre,
      COALESCE(categoria, 'SIN CATEGORIA') AS categoria,
      SUM(cantidad) AS unidades,
      SUM(sub_total) AS total_vendido,
      ROUND(SUM(sub_total) / NULLIF(SUM(cantidad), 0), 2) AS precio_promedio_unitario
    FROM {view_name}
    {where_sql}
    GROUP BY id_producto_combo, nombre, COALESCE(categoria, 'SIN CATEGORIA')
    ORDER BY {order_expr}
    LIMIT {int(limit)};
    """

def q_por_usuario(view_name: str, where_sql: str) -> str:
    return f"""
    SELECT
      usuario_reg,
      SUM(sub_total) AS total_vendido,
      COUNT(DISTINCT id_comanda) AS comandas,
      SUM(cantidad) AS items,
      ROUND(SUM(sub_total) / NULLIF(COUNT(DISTINCT id_comanda), 0), 2) AS ticket_promedio,
      SUM(CASE WHEN tipo_salida = 'CORTESIA' THEN sub_total ELSE 0 END) AS monto_cortesia,
      COUNT(DISTINCT CASE WHEN tipo_salida = 'CORTESIA' THEN id_comanda END) AS comandas_cortesia
    FROM {view_name}
    {where_sql}
    GROUP BY usuario_reg
    ORDER BY total_vendido DESC;
    """

def q_prefacturacion(view_name: str, where_sql: str) -> str:

  # 🟡 Futuro / no implementado aún en el repo (idea documentada)
    return f"""
    SELECT
      SUM(CASE WHEN (id_factura IS NOT NULL OR nro_factura IS NOT NULL) THEN sub_total ELSE 0 END) AS monto_facturado,
      SUM(CASE WHEN (id_factura IS NULL AND nro_factura IS NULL) THEN sub_total ELSE 0 END)       AS monto_no_facturado,

      COUNT(DISTINCT CASE WHEN (id_factura IS NOT NULL OR nro_factura IS NOT NULL) THEN id_comanda END) AS comandas_facturadas,
      COUNT(DISTINCT CASE WHEN (id_factura IS NULL AND nro_factura IS NULL) THEN id_comanda END)       AS comandas_no_facturadas
    FROM {view_name}
    {where_sql};
    """

def q_detalle(view_name: str, where_sql: str, limit: int = 500) -> str:
    return f"""
    SELECT
      fecha_emision,
      id_operacion,
      id_comanda,
      id_mesa,
      usuario_reg,
      nombre,
      categoria,
      cantidad,
      precio_venta,
      sub_total,
      tipo_salida,
      estado_comanda,
      estado_impresion,
      id_factura,
      nro_factura
    FROM {view_name}
    {where_sql}
    ORDER BY fecha_emision DESC
    LIMIT {int(limit)};
    """
```

### 3.3 `db.py` (helper mínimo)

✅ En este repo, `src/db.py` usa `st.connection(..., type="sql")` (Streamlit Connections).
El ejemplo con `create_engine` es **alternativo** y aplica si se decide no usar Connections.

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

```python
# src/metrics.py
from .db import read_df
from .query_store import (
    Filters, build_where,
    q_kpis, q_ventas_por_hora, q_por_categoria, q_top_productos,
    q_por_usuario, q_prefacturacion, q_detalle
)

def get_dashboard_data(view_name: str, f: Filters, mode: str):
    where_sql, params = build_where(f, mode)

    kpis = read_df(q_kpis(view_name, where_sql), params).iloc[0].to_dict()
    por_hora = read_df(q_ventas_por_hora(view_name, where_sql), params)
    por_categoria = read_df(q_por_categoria(view_name, where_sql), params)
    top = read_df(q_top_productos(view_name, where_sql, limit=20), params)
    por_usuario = read_df(q_por_usuario(view_name, where_sql), params)
    prefac = read_df(q_prefacturacion(view_name, where_sql), params).iloc[0].to_dict()
    detalle = read_df(q_detalle(view_name, where_sql, limit=500), params)

    return dict(
        kpis=kpis,
        por_hora=por_hora,
        por_categoria=por_categoria,
        top=top,
        por_usuario=por_usuario,
        prefac=prefac,
        detalle=detalle,
    )
```

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
  - Ventas por hora | Ventas por categoría
  - Top productos   | Ventas por usuario
7. Tabla detalle bajo demanda

### 4.3 Controles de rendimiento
- No cargar detalle si el usuario no lo solicita (tabs/expander).
- No cargar IDs (pendientes/no impresas) si el usuario no lo solicita.
- Para tiempo real: refresco manual (botón “Actualizar”).

### 4.4 Presentación de métricas
- Para un look tipo dashboard, usar `st.metric(..., border=True)`.

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
