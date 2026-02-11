# 🚨 Guía Técnica: Red Flags en Dashback

> Documento de referencia para refactoring gradual del proyecto Dashback.
> Identifica problemas de código/arquitectura con soluciones específicas que preservan la funcionalidad existente.

---

## Resumen Ejecutivo

El proyecto Dashback tiene una **arquitectura sólida** (⭐⭐⭐⭐⭐) con capas bien definidas:
- `app.py` → `metrics.py` → `query_store.py` → `db.py`

Sin embargo, se identificaron **6 red flags** que afectan mantenibilidad, rendimiento y escalabilidad. Este documento propone soluciones incrementales que no rompen funcionalidad existente.

---

## Estado actual (2026-02-11)

Implementado en el proyecto:
- Red Flag #1: JOIN de impresión extraído a helper.
- Red Flag #2: TTL por modo (realtime sin cache, histórico con cache corto).
- Red Flag #3: Healthcheck extendido con vistas P&L.
- Red Flag #4: `app.py` modularizado en `src/ui/sections/`.
- Red Flag #5: Manejo granular de errores en gráficos con retry y fallback por sesión.
- Red Flag #6: Conexión cacheada por sesión con `on_release` + validación opcional.
- Lazy loading real en ítems de comandas.
- `@st.fragment` aplicado a KPIs, márgenes, gráficos y detalle.
- Theming avanzado con Google Fonts, Material Symbols y paleta de charts.

Pendiente / opcional:
- Fallback cache para KPIs/márgenes (solo implementado en gráficos).
- Ajustes de pool/conexión según métricas reales de carga.

---

## 🔴 Red Flag #1: Duplicación de JOINs al Log de Impresión

### Problema

El JOIN a `vw_comanda_ultima_impresion` + `parameter_table` se repite **idéntico** en múltiples funciones de `query_store.py`:

```python
# Se repite en: q_kpis(), q_ventas_por_hora(), q_por_categoria(), 
#               q_top_productos(), q_por_usuario()

LEFT JOIN vw_comanda_ultima_impresion imp
    ON imp.id_comanda = v.id_comanda
LEFT JOIN parameter_table ei_log
    ON ei_log.id = imp.ind_estado_impresion
   AND ei_log.id_master = 10
   AND ei_log.estado = 'HAB'
```

**Impacto**: ~25 líneas duplicadas, alto riesgo de inconsistencia si cambia la lógica.

### Solución Propuesta

Extraer helper privado que genere el fragmento SQL:

```python
# src/query_store.py

def _join_impresion_log(*, table_alias: str = "v") -> str:
    """Genera el JOIN al log de impresión para señal alternativa de IMPRESO.
    
    Uso: cuando `use_impresion_log=True` en queries de ventas.
    Requiere alias `ei_log` para la condición de venta efectiva.
    """
    return f"""
    LEFT JOIN vw_comanda_ultima_impresion imp
        ON imp.id_comanda = {table_alias}.id_comanda
    LEFT JOIN parameter_table ei_log
        ON ei_log.id = imp.ind_estado_impresion
       AND ei_log.id_master = 10
       AND ei_log.estado = 'HAB'
    """


def q_ventas_por_hora(view_name: str, where_sql: str, *, use_impresion_log: bool = False) -> str:
    cond = _cond_venta_final("v") if not use_impresion_log else _cond_venta_final_impreso_log()
    where2 = _append_condition(where_sql, cond)
    
    join_sql = _join_impresion_log() if use_impresion_log else ""
    
    return f"""
        SELECT
            HOUR(v.fecha_emision) AS hora,
            ...
        FROM {view_name} v
        {join_sql}
        {where2}
        ...
    """
```

**Beneficio**: Una sola fuente de verdad para el JOIN, fácil de mantener.

---

## 🔴 Red Flag #2: Sin Cache para Consultas Históricas

### Problema

Todas las consultas se ejecutan sin TTL, incluso en modo histórico donde los datos **no cambian**:

```python
# src/query_store.py - fetch_dataframe()
return conn.query(query, params=params or {}, ttl=0)  # ⚠️ ttl=0 = sin cache
```

**Impacto**: Consultas repetidas innecesarias en producción, especialmente al navegar entre pestañas/expanders.

### Solución Propuesta

Implementar cache con TTL diferenciado según contexto:

```python
# src/query_store.py

def fetch_dataframe(
    conn: Any, 
    query: str, 
    params: dict[str, Any] | None = None,
    *,
    ttl: int | None = None,  # Nuevo parámetro
) -> pd.DataFrame:
    """Ejecuta SELECT y retorna DataFrame.
    
    Args:
        ttl: Segundos de cache. None = usar default de Streamlit.
             0 = sin cache (para tiempo real).
             300 = 5 min (recomendado para histórico).
    """
    if hasattr(conn, "query"):
        try:
            return conn.query(query, params=params or {}, ttl=ttl or 0)
        except TypeError:
            return conn.query(query, params=params or {})
    # ... resto del código para mysql.connector
```

En `metrics.py`, pasar TTL según modo:

```python
# src/metrics.py

def get_kpis(conn: Any, view_name: str, filters: Filters, mode: str) -> dict[str, Any]:
    where_sql, params = build_where(filters, mode, table_alias="v")
    sql = q_kpis(view_name, where_sql)
    
    # Cache solo para histórico (datos inmutables)
    cache_ttl = 300 if mode in ("ops", "dates") else 0
    
    df = _run_df(conn, sql, params, context="Error ejecutando KPIs", ttl=cache_ttl)
    # ...
```

**Nota Streamlit 1.53+**: Ver sección de `st.cache_data(scope="session")` para cache por usuario.

---

## 🔴 Red Flag #3: Healthcheck Incompleto

### Problema

El healthcheck actual (`Q_HEALTHCHECK`) valida la existencia de vistas pero **no verifica** las vistas de márgenes que son críticas para P&L:

```sql
-- Vistas verificadas actualmente:
comandas_v6, comandas_v6_todas, comandas_v6_base, comandas_v7,
vw_comanda_ultima_impresion, bar_comanda_impresion

-- ⚠️ FALTAN (usadas en Márgenes & Rentabilidad):
vw_margen_comanda
vw_consumo_valorizado_operativa
vw_consumo_insumos_operativa
vw_cogs_comanda
```

**Impacto**: El dashboard puede mostrar errores crípticos si faltan vistas de márgenes.

### Solución Propuesta

Extender `Q_HEALTHCHECK` con las vistas faltantes:

```sql
-- src/query_store.py

Q_HEALTHCHECK = """
SELECT
    req.object_name,
    req.category,
    CASE WHEN t.TABLE_NAME IS NULL THEN 0 ELSE 1 END AS exists_in_db,
    t.TABLE_TYPE AS object_type,
    DATABASE() AS database_name
FROM (
    -- Core: comandas
    SELECT 'comandas_v6' AS object_name, 'core' AS category
    UNION ALL SELECT 'comandas_v6_todas', 'core'
    UNION ALL SELECT 'comandas_v6_base', 'core'
    
    -- Diagnóstico: impresión
    UNION ALL SELECT 'comandas_v7', 'diagnostico'
    UNION ALL SELECT 'vw_comanda_ultima_impresion', 'diagnostico'
    UNION ALL SELECT 'bar_comanda_impresion', 'diagnostico'
    
    -- P&L: márgenes y costos
    UNION ALL SELECT 'vw_margen_comanda', 'pnl'
    UNION ALL SELECT 'vw_consumo_valorizado_operativa', 'pnl'
    UNION ALL SELECT 'vw_consumo_insumos_operativa', 'pnl'
    UNION ALL SELECT 'vw_cogs_comanda', 'pnl'
) req
LEFT JOIN information_schema.TABLES t
    ON t.TABLE_SCHEMA = DATABASE()
 AND t.TABLE_NAME = req.object_name
ORDER BY req.category, req.object_name;
"""
```

En la UI, mostrar advertencias diferenciadas:

```python
# app.py

if missing:
    core_missing = [m for m in missing if m in ('comandas_v6', 'comandas_v6_todas', 'comandas_v6_base')]
    pnl_missing = [m for m in missing if m.startswith('vw_')]
    
    if core_missing:
        st.error(f"❌ Faltan vistas críticas (core): {', '.join(core_missing)}")
    if pnl_missing:
        st.warning(f"⚠️ Faltan vistas de márgenes (P&L): {', '.join(pnl_missing)} — El bloque Márgenes & Rentabilidad no funcionará.")
```

---

## 🔴 Red Flag #4: app.py con +600 Líneas

### Problema

`app.py` tiene **~650 líneas** mezclando:
- Configuración y estilos CSS
- Lógica de conexión y startup
- KPIs y métricas
- Gráficos (4 secciones)
- Expanders de detalle (5+)
- Manejo de errores

**Impacto**: Difícil de navegar, testear y mantener.

### Solución Propuesta

Modularizar en secciones UI sin cambiar comportamiento:

```
src/ui/
├── __init__.py
├── components.py      # (ya existe) Gráficos Plotly
├── formatting.py      # (ya existe) Formato Bolivia
├── layout.py          # (ya existe) Header, sidebar
├── sections/          # NUEVO: secciones del dashboard
│   ├── __init__.py
│   ├── kpis.py        # render_kpis_section()
│   ├── margenes.py    # render_margenes_section()
│   ├── estado.py      # render_estado_operativo_section()
│   ├── graficos.py    # render_charts_section()
│   └── detalle.py     # render_detalle_section()
└── styles.py          # NUEVO: CSS inyectado
```

Ejemplo de refactor para KPIs:

```python
# src/ui/sections/kpis.py

from __future__ import annotations
from typing import Any, Callable

import streamlit as st

from src.metrics import get_kpis, get_actividad_emision_comandas, QueryExecutionError
from src.ui.formatting import format_bs, format_int


def render_kpis_section(
    conn: Any,
    startup: Any,
    filters: Any,
    mode: str,
    *,
    ventas_use_impresion_log: bool = False,
    debug_fn: Callable[[Exception], None] | None = None,
) -> None:
    """Renderiza la sección de KPIs principales."""
    
    st.subheader("KPIs")
    
    if conn is None or startup is None:
        st.info("Conecta a la base de datos para ver KPIs.")
        return
    
    try:
        kpis = get_kpis(conn, startup.view_name, filters, mode)
        
        # ... lógica de renderizado de métricas ...
        
    except Exception as exc:
        st.error(f"Error calculando KPIs: {exc}")
        if debug_fn:
            debug_fn(exc)
```

En `app.py`, el código se reduce a:

```python
# app.py (simplificado)

from src.ui.sections.kpis import render_kpis_section
from src.ui.sections.margenes import render_margenes_section
# ...

render_kpis_section(conn, startup, filters, mode_for_metrics, 
                    ventas_use_impresion_log=ventas_use_impresion_log,
                    debug_fn=_maybe_render_sql_debug)

render_margenes_section(conn, startup, filters, mode_for_metrics,
                        debug_fn=_maybe_render_sql_debug)
# ...
```

**Beneficio**: Cada sección es testeable de forma aislada, `app.py` queda como orquestador.

---

## 🔴 Red Flag #5: Sin Manejo Granular de Errores por Gráfico

### Problema

Si un gráfico falla, el bloque completo muestra error. No hay degradación graceful:

```python
# Actual: si get_ventas_por_hora() falla, no se ve nada del bloque g1
with g1:
    render_chart_section(
        title="Ventas por hora",
        data_fn=partial(get_ventas_por_hora, ...),
        ...
    )
```

**Impacto**: Un error en una vista/query afecta la visualización de todo el dashboard.

### Solución Propuesta

Ya existe `render_chart_section()` con try/except, pero mejorar el feedback:

```python
# src/ui/components.py

def render_chart_section(
    # ... params existentes ...
    fallback_data: pd.DataFrame | None = None,  # NUEVO
    show_retry: bool = True,  # NUEVO
) -> None:
    """Helper para renderizar secciones de gráficos con degradación graceful."""
    
    st.subheader(title)
    st.caption(caption)
    
    if conn is None or startup is None:
        st.info(f"Conecta a la base de datos para ver {title.lower()}.")
        return
    
    try:
        df = data_fn()
        
        if df is None or df.empty:
            # ... manejo de vacío existente ...
            pass
        else:
            fig = chart_fn(df)
            st.plotly_chart(fig, width="stretch")
            
            if allow_csv_export:
                # ... export existente ...
                pass
                
    except Exception as exc:
        # Degradación graceful: mostrar mensaje pero no romper el dashboard
        st.warning(f"⚠️ No se pudo cargar {title.lower()}")
        
        with st.expander("Ver detalles del error", expanded=False):
            st.error(str(exc))
            if debug_fn:
                debug_fn(exc)
        
        # Opción de reintentar
        if show_retry:
            if st.button(f"🔄 Reintentar {title}", key=f"retry_{title.lower().replace(' ', '_')}"):
                st.rerun()
        
        # Mostrar datos de fallback si existen
        if fallback_data is not None and not fallback_data.empty:
            st.caption("Mostrando datos en cache:")
            st.dataframe(fallback_data, width="stretch")
```

---

## 🔴 Red Flag #6: Conexión sin Validación de Pool/Límites

### Problema

`get_connection()` usa `@st.cache_resource` pero no valida:
- Si la conexión sigue viva
- Límites de conexiones simultáneas
- Timeout de queries largas

```python
# src/db.py

@st.cache_resource(show_spinner=False)
def get_connection(connection_name: str = "mysql") -> SQLConnection:
    return cast(SQLConnection, st.connection(connection_name, type="sql"))
```

### Solución Propuesta (Streamlit 1.53+)

Aprovechar las nuevas características de cache:

```python
# src/db.py

from __future__ import annotations
from typing import cast
import streamlit as st
from streamlit.connections.sql_connection import SQLConnection


def _cleanup_connection(conn: SQLConnection) -> None:
    """Callback para liberar recursos al cerrar sesión."""
    try:
        # SQLConnection maneja el pool internamente, pero podemos loggear
        import logging
        logging.info(f"Liberando conexión: {conn}")
    except Exception:
        pass


@st.cache_resource(
    show_spinner=False,
    # Nuevo en 1.53: scope por sesión (cada usuario tiene su conexión)
    # scope="session",  # Descomentar si se requiere aislamiento por usuario
    # Nuevo en 1.53: callback de limpieza
    # on_release=_cleanup_connection,  # Descomentar para cleanup
)
def get_connection(connection_name: str = "mysql") -> SQLConnection:
    """Devuelve la conexión MySQL configurada en `.streamlit/secrets.toml`.
    
    Notas de rendimiento:
    - La conexión se cachea globalmente (default) o por sesión (scope="session").
    - Streamlit Connections maneja el pool internamente.
    - Para producción, considerar límites en la URL de conexión:
      mysql+mysqlconnector://user:pass@host:3306/db?pool_size=5&pool_recycle=3600
    """
    return cast(SQLConnection, st.connection(connection_name, type="sql"))


def validate_connection(conn: SQLConnection) -> bool:
    """Valida que la conexión esté activa."""
    try:
        from src.query_store import fetch_dataframe
        df = fetch_dataframe(conn, "SELECT 1 AS ping")
        return df is not None and not df.empty
    except Exception:
        return False
```

---

## 🟡 Mejoras Adicionales Sugeridas

### 1. Comparativa Día Anterior

Agregar delta visual en KPIs comparando con el día anterior:

```python
# src/metrics.py

def get_kpis_with_comparison(
    conn: Any, 
    view_name: str, 
    filters: Filters, 
    mode: str,
) -> dict[str, Any]:
    """KPIs con comparativa vs día/operativa anterior."""
    
    current = get_kpis(conn, view_name, filters, mode)
    
    # Calcular filtros del período anterior
    if mode == "ops" and filters.op_ini and filters.op_fin:
        prev_filters = Filters(
            op_ini=filters.op_ini - 1,
            op_fin=filters.op_fin - 1,
        )
    elif mode == "dates" and filters.dt_ini and filters.dt_fin:
        from datetime import datetime, timedelta
        dt_ini = datetime.strptime(filters.dt_ini[:10], "%Y-%m-%d")
        dt_fin = datetime.strptime(filters.dt_fin[:10], "%Y-%m-%d")
        delta = dt_fin - dt_ini
        prev_filters = Filters(
            dt_ini=f"{(dt_ini - delta - timedelta(days=1)).strftime('%Y-%m-%d')} 00:00:00",
            dt_fin=f"{(dt_ini - timedelta(days=1)).strftime('%Y-%m-%d')} 23:59:59",
        )
    else:
        return {**current, "has_comparison": False}
    
    previous = get_kpis(conn, view_name, prev_filters, mode)
    
    return {
        **current,
        "has_comparison": True,
        "prev_total_vendido": previous.get("total_vendido", 0),
        "prev_total_comandas": previous.get("total_comandas", 0),
        "delta_vendido": current.get("total_vendido", 0) - previous.get("total_vendido", 0),
        "delta_comandas": current.get("total_comandas", 0) - previous.get("total_comandas", 0),
    }
```

En la UI:

```python
# En render_kpis_section()

c1.metric(
    "Total vendido",
    format_bs(kpis["total_vendido"]),
    delta=format_bs(kpis.get("delta_vendido")) if kpis.get("has_comparison") else None,
    delta_color="normal",  # Nuevo en 1.53: colores configurables
    help="...",
    border=True,
)
```

### 2. Sparklines en Métricas

Streamlit 1.53+ soporta `st.metric` con datos de tendencia (experimental):

```python
# Cuando esté disponible en st.metric:
c1.metric(
    "Total vendido",
    format_bs(kpis["total_vendido"]),
    delta=format_bs(delta),
    # chart_data=trend_df["total_vendido"].tail(7).tolist(),  # Futuro
)
```

Mientras tanto, usar mini-gráficos con Plotly:

```python
# src/ui/components.py

def sparkline(data: list[float], height: int = 30) -> Any:
    """Mini gráfico de tendencia para métricas."""
    import plotly.graph_objects as go
    
    fig = go.Figure(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color='#2E86DE', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(46,134,222,0.1)',
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    
    return fig
```

### 3. Alertas por Umbral

Destacar métricas que superen umbrales configurables:

```python
# src/ui/sections/kpis.py

THRESHOLDS = {
    "ticket_promedio_min": 50.0,  # Bs
    "minutos_desde_ultima_max": 30,  # minutos
}

def _metric_with_alert(
    container: Any,
    label: str,
    value: str,
    threshold_key: str | None = None,
    current_value: float | None = None,
    **kwargs,
) -> None:
    """Renderiza métrica con alerta visual si supera umbral."""
    
    is_alert = False
    if threshold_key and current_value is not None:
        threshold = THRESHOLDS.get(threshold_key)
        if threshold:
            if threshold_key.endswith("_min"):
                is_alert = current_value < threshold
            elif threshold_key.endswith("_max"):
                is_alert = current_value > threshold
    
    # Agregar emoji de alerta al label si aplica
    if is_alert:
        label = f"⚠️ {label}"
    
    container.metric(label, value, **kwargs)
```

### 4. Export CSV Mejorado

El export actual funciona, pero se puede mejorar:

```python
# src/ui/components.py

def export_csv_button(
    df: pd.DataFrame,
    filename: str,
    *,
    include_timestamp: bool = True,
    format_money: bool = True,
) -> None:
    """Botón de exportación CSV con opciones."""
    
    from datetime import datetime
    
    if include_timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{ts}.csv"
    
    # Formatear montos para Excel (sin Bs, con separador estándar)
    export_df = df.copy()
    if format_money:
        for col in export_df.select_dtypes(include=['float64', 'int64']).columns:
            if any(kw in col.lower() for kw in ['vendido', 'cogs', 'margen', 'total', 'precio']):
                export_df[col] = export_df[col].round(2)
    
    csv_data = export_df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    
    st.download_button(
        label="📥 Exportar CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
```

---

## 📋 Checklist de Implementación

| Prioridad | Red Flag | Esfuerzo | Riesgo |
|-----------|----------|----------|--------|
| 🔴 Alta | #2 Cache TTL | Bajo | Bajo |
| 🔴 Alta | #3 Healthcheck | Bajo | Bajo |
| 🟠 Media | #1 JOIN helper | Bajo | Bajo |
| 🟠 Media | #5 Errores granulares | Medio | Bajo |
| 🟡 Baja | #4 Modularizar app.py | Alto | Medio |
| 🟡 Baja | #6 Conexión validada | Medio | Bajo |

### Orden Recomendado

1. **Semana 1**: Cache TTL (#2) + Healthcheck (#3) — Impacto inmediato en rendimiento
2. **Semana 2**: JOIN helper (#1) + Errores granulares (#5) — Limpieza de código
3. **Sprint futuro**: Modularización (#4) — Requiere tests previos

---

## 🔗 Referencias

- [docs/02-guia_dashboard_backstage.md](../../docs/02-guia_dashboard_backstage.md) — Arquitectura y vistas
- [docs/03-evolucion_y_mejoras.md](../../docs/03-evolucion_y_mejoras.md) — Historial de cambios
- [Streamlit 1.53 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes) — Nuevas features de cache
- [Streamlit 1.54 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes) — Chart theming

---

*Documento generado: 2026-02-10*
*Versión de Streamlit objetivo: 1.54.0*
