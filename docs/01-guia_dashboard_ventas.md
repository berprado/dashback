# Guía Completa: Dashboard de Ventas con Python, Streamlit y MySQL

## Información del Proyecto
- **Python:** 3.12.2
- **Streamlit:** 1.52.0
- **MySQL:** 5.6.12
- **Sistema Operativo:** Windows 10
- **IDE:** Visual Studio Code
- **Gestor de BD:** dbForge Studio for MySQL

---

## FASE 1: Preparación del Entorno de Trabajo

### Paso 1.1: Crear la carpeta del proyecto

Abre **PowerShell** o **CMD** y ejecuta:

```powershell
# Navegar al Desktop
cd C:\Users\Bernardo\Desktop

# Crear la carpeta del proyecto
mkdir dashboard_ventas

# Entrar a la carpeta
cd dashboard_ventas
```

> **💡 Nota:** Puedes nombrar la carpeta como prefieras. Usamos `dashboard_ventas` como ejemplo descriptivo.

---

### Paso 1.2: Abrir el proyecto en VS Code

Desde la misma terminal, ejecuta:

```powershell
code .
```

Esto abrirá VS Code directamente en la carpeta del proyecto.

> **💡 Alternativa:** También puedes abrir VS Code manualmente y usar `File > Open Folder` para seleccionar la carpeta.

---

### Paso 1.3: Abrir la terminal integrada de VS Code

Una vez en VS Code:
1. Presiona `Ctrl + ñ` (o `Ctrl + `` ` en teclado inglés)
2. O ve a `Terminal > New Terminal` en el menú superior

Verás algo así:
```
PS C:\Users\Bernardo\Desktop\dashboard_ventas>
```

---

### Paso 1.4: Crear el entorno virtual

En la terminal de VS Code, ejecuta:

```powershell
python -m venv .venv
```

> **¿Qué hace este comando?**
> - `python -m venv` → Ejecuta el módulo venv de Python
> - `.venv` → Nombre de la carpeta del entorno virtual (el punto la hace "oculta")

Verás que se crea una carpeta `.venv` en tu proyecto.

---

### Paso 1.5: Activar el entorno virtual

```powershell
.\.venv\Scripts\Activate
```

**Confirmación:** Tu terminal ahora debe verse así:
```
(.venv) PS C:\Users\Bernardo\Desktop\dashboard_ventas>
```

El `(.venv)` al inicio indica que el entorno está activo.

> **⚠️ Importante:** Cada vez que abras VS Code o una nueva terminal, deberás activar el entorno virtual nuevamente.

---

### Paso 1.6: Configurar VS Code para usar el entorno virtual

1. Presiona `Ctrl + Shift + P`
2. Escribe: `Python: Select Interpreter`
3. Selecciona la opción que muestre `.venv` en la ruta, por ejemplo:
   ```
   Python 3.12.2 ('.venv': venv) .\venv\Scripts\python.exe
   ```

Esto asegura que VS Code use el intérprete correcto.

---

## FASE 2: Instalación de Dependencias

### Paso 2.1: Actualizar pip

Antes de instalar paquetes, actualiza pip:

```powershell
python -m pip install --upgrade pip
```

---

### Paso 2.2: Instalar las librerías necesarias

Ejecuta el siguiente comando (todo en una línea):

```powershell
pip install streamlit==1.52.0 mysql-connector-python pandas plotly python-dotenv
```

**¿Qué instala cada librería?**

| Librería | Versión | Propósito |
|----------|---------|-----------|
| `streamlit` | 1.52.0 | Framework para crear el dashboard web |
| `mysql-connector-python` | (última) | Conector oficial de MySQL para Python |
| `pandas` | (última) | Manipulación y análisis de datos |
| `plotly` | (última) | Gráficos interactivos |
| `python-dotenv` | (última) | Manejo seguro de credenciales |

---

### Paso 2.3: Verificar la instalación

```powershell
pip list
```

Deberías ver las librerías instaladas con sus versiones.

---

### Paso 2.4: Crear el archivo requirements.txt

Este archivo documenta las dependencias del proyecto:

```powershell
pip freeze > requirements.txt
```

> **¿Para qué sirve?** Si en el futuro necesitas recrear el entorno (o compartir el proyecto), solo ejecutas:
> ```powershell
> pip install -r requirements.txt
> ```

---

## FASE 3: Estructura del Proyecto

### Paso 3.1: Crear la estructura de carpetas y archivos

En VS Code, crea la siguiente estructura:

```
dashboard_ventas/
│
├── .venv/                  # Entorno virtual (ya existe)
├── .env                    # Credenciales de BD (crear)
├── .gitignore              # Archivos a ignorar en Git (crear)
├── requirements.txt        # Dependencias (ya existe)
│
├── config/                 # Configuración
│   └── database.py         # Conexión a MySQL
│
├── data/                   # Módulos de datos
│   └── queries.py          # Consultas SQL
│
├── components/             # Componentes visuales
│   └── charts.py           # Funciones para gráficos
│
└── app.py                  # Aplicación principal
```

**Para crear carpetas en VS Code:**
1. Clic derecho en el explorador de archivos (panel izquierdo)
2. Selecciona `New Folder`

**Para crear archivos:**
1. Clic derecho en la carpeta correspondiente
2. Selecciona `New File`

---

## FASE 4: Configuración de Conexión a MySQL

### Paso 4.1: Crear el archivo .env (credenciales)

Crea el archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
# Configuración de Base de Datos MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=adminerp_copy
```

> **⚠️ Importante:** 
> - Reemplaza `tu_usuario` y `tu_contraseña` con tus credenciales reales
> - Este archivo NUNCA debe subirse a Git (contiene información sensible)

---

### Paso 4.2: Crear el archivo .gitignore

Crea el archivo `.gitignore` en la raíz del proyecto:

```gitignore
# Entorno virtual
.venv/
venv/
ENV/

# Variables de entorno (credenciales)
.env

# Archivos de Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Archivos de VS Code
.vscode/

# Archivos del sistema
.DS_Store
Thumbs.db
```

---

### Paso 4.3: Crear el módulo de conexión a MySQL

Crea el archivo `config/database.py`:

```python
"""
Módulo de conexión a la base de datos MySQL.
Proporciona funciones para conectar y ejecutar consultas.
"""

import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import pandas as pd

# Cargar variables de entorno desde .env
load_dotenv()


def get_connection():
    """
    Crea y retorna una conexión a la base de datos MySQL.
    
    Returns:
        connection: Objeto de conexión MySQL o None si falla
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        
        if connection.is_connected():
            return connection
            
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None


def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """
    Ejecuta una consulta SQL y retorna los resultados como DataFrame.
    
    Args:
        query: Consulta SQL a ejecutar
        params: Parámetros opcionales para la consulta
        
    Returns:
        DataFrame con los resultados o DataFrame vacío si hay error
    """
    connection = get_connection()
    
    if connection is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql(query, connection, params=params)
        return df
        
    except Error as e:
        print(f"Error al ejecutar consulta: {e}")
        return pd.DataFrame()
        
    finally:
        if connection.is_connected():
            connection.close()


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos.
    
    Returns:
        True si la conexión es exitosa, False en caso contrario
    """
    connection = get_connection()
    
    if connection is not None and connection.is_connected():
        db_info = connection.get_server_info()
        print(f"✅ Conexión exitosa a MySQL versión: {db_info}")
        connection.close()
        return True
    
    print("❌ No se pudo conectar a la base de datos")
    return False
```

---

### Paso 4.4: Probar la conexión

Crea un archivo temporal `test_connection.py` en la raíz:

```python
"""Script para probar la conexión a la base de datos."""

from config.database import test_connection

if __name__ == "__main__":
    test_connection()
```

Ejecuta en la terminal:

```powershell
python test_connection.py
```

**Resultado esperado:**
```
✅ Conexión exitosa a MySQL versión: 5.6.12
```

> Si ves un error, verifica:
> 1. Que MySQL esté ejecutándose
> 2. Que las credenciales en `.env` sean correctas
> 3. Que el nombre de la base de datos sea correcto

---

## FASE 5: Crear el Módulo de Consultas

### Paso 5.1: Crear las consultas SQL

Crea el archivo `data/queries.py`:

```python
"""
Módulo de consultas SQL para el dashboard de ventas.
Contiene todas las consultas utilizadas en la aplicación.
"""

from config.database import execute_query
import pandas as pd


def get_ventas_por_fecha(fecha_inicio: str = None, fecha_fin: str = None) -> pd.DataFrame:
    """
    Obtiene el resumen de ventas agrupado por fecha.
    
    Args:
        fecha_inicio: Fecha inicial del rango (formato: 'YYYY-MM-DD')
        fecha_fin: Fecha final del rango (formato: 'YYYY-MM-DD')
    
    Returns:
        DataFrame con fecha, cantidad de items y total de ventas
    """
    query = """
        SELECT 
            DATE(fecha_emision) as fecha,
            COUNT(*) as cantidad_items,
            SUM(sub_total) as total_ventas
        FROM comandas_v6_base
        WHERE 1=1
    """
    
    if fecha_inicio:
        query += f" AND DATE(fecha_emision) >= '{fecha_inicio}'"
    if fecha_fin:
        query += f" AND DATE(fecha_emision) <= '{fecha_fin}'"
    
    query += " GROUP BY DATE(fecha_emision) ORDER BY fecha DESC"
    
    return execute_query(query)


def get_ventas_por_categoria() -> pd.DataFrame:
    """
    Obtiene el total de ventas agrupado por categoría de producto.
    
    Returns:
        DataFrame con categoría, cantidad y total de ventas
    """
    query = """
        SELECT 
            COALESCE(categoria, 'Sin Categoría') as categoria,
            SUM(cantidad) as cantidad_items,
            SUM(sub_total) as total_ventas
        FROM comandas_v6_base
        GROUP BY categoria
        ORDER BY total_ventas DESC
    """
    return execute_query(query)


def get_productos_mas_vendidos(limite: int = 10) -> pd.DataFrame:
    """
    Obtiene los productos más vendidos.
    
    Args:
        limite: Cantidad de productos a mostrar
        
    Returns:
        DataFrame con nombre del producto, cantidad vendida y total
    """
    query = f"""
        SELECT 
            nombre,
            SUM(cantidad) as cantidad_vendida,
            SUM(sub_total) as total_ventas
        FROM comandas_v6_base
        WHERE nombre IS NOT NULL
        GROUP BY nombre
        ORDER BY cantidad_vendida DESC
        LIMIT {limite}
    """
    return execute_query(query)


def get_ventas_por_usuario() -> pd.DataFrame:
    """
    Obtiene el resumen de ventas por usuario/vendedor.
    
    Returns:
        DataFrame con usuario, cantidad de comandas y total de ventas
    """
    query = """
        SELECT 
            usuario_reg as usuario,
            COUNT(DISTINCT id_comanda) as total_comandas,
            SUM(sub_total) as total_ventas
        FROM comandas_v6_base
        GROUP BY usuario_reg
        ORDER BY total_ventas DESC
    """
    return execute_query(query)


def get_resumen_general() -> dict:
    """
    Obtiene métricas generales para los KPIs del dashboard.
    
    Returns:
        Diccionario con métricas: total_ventas, total_comandas, 
        ticket_promedio, total_productos
    """
    query = """
        SELECT 
            SUM(sub_total) as total_ventas,
            COUNT(DISTINCT id_comanda) as total_comandas,
            AVG(sub_total) as ticket_promedio,
            COUNT(DISTINCT nombre) as total_productos
        FROM comandas_v6_base
    """
    df = execute_query(query)
    
    if df.empty:
        return {
            'total_ventas': 0,
            'total_comandas': 0,
            'ticket_promedio': 0,
            'total_productos': 0
        }
    
    return df.iloc[0].to_dict()


def get_ventas_por_tipo_salida() -> pd.DataFrame:
    """
    Obtiene las ventas agrupadas por tipo de salida.
    
    Returns:
        DataFrame con tipo de salida y totales
    """
    query = """
        SELECT 
            COALESCE(tipo_salida, 'No especificado') as tipo_salida,
            COUNT(*) as cantidad,
            SUM(sub_total) as total_ventas
        FROM comandas_v6_base
        GROUP BY tipo_salida
        ORDER BY total_ventas DESC
    """
    return execute_query(query)
```

---

## FASE 6: Crear el Módulo de Gráficos

### Paso 6.1: Crear los componentes visuales

Crea el archivo `components/charts.py`:

```python
"""
Módulo de gráficos para el dashboard.
Contiene funciones para crear visualizaciones con Plotly.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def grafico_ventas_tiempo(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de líneas de ventas en el tiempo.
    
    Args:
        df: DataFrame con columnas 'fecha' y 'total_ventas'
        
    Returns:
        Figura de Plotly
    """
    fig = px.line(
        df,
        x='fecha',
        y='total_ventas',
        title='Evolución de Ventas',
        labels={'fecha': 'Fecha', 'total_ventas': 'Total Ventas (Bs)'}
    )
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Ventas (Bs)",
        hovermode='x unified'
    )
    return fig


def grafico_categorias(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de pastel de ventas por categoría.
    
    Args:
        df: DataFrame con columnas 'categoria' y 'total_ventas'
        
    Returns:
        Figura de Plotly
    """
    fig = px.pie(
        df,
        values='total_ventas',
        names='categoria',
        title='Distribución de Ventas por Categoría',
        hole=0.4  # Hace un gráfico de dona
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig


def grafico_productos_top(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de barras horizontales de productos más vendidos.
    
    Args:
        df: DataFrame con columnas 'nombre' y 'cantidad_vendida'
        
    Returns:
        Figura de Plotly
    """
    # Ordenar de menor a mayor para que el más vendido quede arriba
    df_sorted = df.sort_values('cantidad_vendida', ascending=True)
    
    fig = px.bar(
        df_sorted,
        x='cantidad_vendida',
        y='nombre',
        orientation='h',
        title='Top 10 Productos Más Vendidos',
        labels={'cantidad_vendida': 'Cantidad Vendida', 'nombre': 'Producto'},
        color='cantidad_vendida',
        color_continuous_scale='Blues'
    )
    fig.update_layout(showlegend=False)
    return fig


def grafico_ventas_usuario(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de barras de ventas por usuario.
    
    Args:
        df: DataFrame con columnas 'usuario' y 'total_ventas'
        
    Returns:
        Figura de Plotly
    """
    fig = px.bar(
        df,
        x='usuario',
        y='total_ventas',
        title='Ventas por Usuario',
        labels={'usuario': 'Usuario', 'total_ventas': 'Total Ventas (Bs)'},
        color='total_ventas',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(showlegend=False)
    return fig
```

---

## FASE 7: Crear la Aplicación Principal

### Paso 7.1: Crear el dashboard

Crea el archivo `app.py` en la raíz del proyecto:

```python
"""
Dashboard de Ventas - Aplicación Principal
Desarrollado con Streamlit, MySQL y Plotly
"""

import streamlit as st
from datetime import datetime, timedelta

# Importar módulos propios
from data.queries import (
    get_ventas_por_fecha,
    get_ventas_por_categoria,
    get_productos_mas_vendidos,
    get_ventas_por_usuario,
    get_resumen_general,
    get_ventas_por_tipo_salida
)
from components.charts import (
    grafico_ventas_tiempo,
    grafico_categorias,
    grafico_productos_top,
    grafico_ventas_usuario
)

# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================
st.set_page_config(
    page_title="Dashboard de Ventas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# TÍTULO PRINCIPAL
# ============================================
st.title("📊 Dashboard de Ventas")
st.markdown("---")

# ============================================
# BARRA LATERAL (FILTROS)
# ============================================
with st.sidebar:
    st.header("🔧 Filtros")
    
    # Filtro de fechas
    st.subheader("Rango de Fechas")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            value=datetime.now() - timedelta(days=30)
        )
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            value=datetime.now()
        )
    
    st.markdown("---")
    
    # Información adicional
    st.info("💡 Los datos se actualizan en tiempo real desde la base de datos.")

# ============================================
# KPIs PRINCIPALES
# ============================================
st.subheader("📈 Indicadores Principales")

resumen = get_resumen_general()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Total Ventas",
        value=f"Bs {resumen['total_ventas']:,.2f}" if resumen['total_ventas'] else "Bs 0.00"
    )

with col2:
    st.metric(
        label="🧾 Total Comandas",
        value=f"{resumen['total_comandas']:,}" if resumen['total_comandas'] else "0"
    )

with col3:
    st.metric(
        label="📊 Ticket Promedio",
        value=f"Bs {resumen['ticket_promedio']:,.2f}" if resumen['ticket_promedio'] else "Bs 0.00"
    )

with col4:
    st.metric(
        label="📦 Productos Vendidos",
        value=f"{resumen['total_productos']:,}" if resumen['total_productos'] else "0"
    )

st.markdown("---")

# ============================================
# GRÁFICOS - FILA 1
# ============================================
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("📅 Ventas en el Tiempo")
    df_ventas_fecha = get_ventas_por_fecha(
        str(fecha_inicio),
        str(fecha_fin)
    )
    
    if not df_ventas_fecha.empty:
        fig_tiempo = grafico_ventas_tiempo(df_ventas_fecha)
        st.plotly_chart(fig_tiempo, use_container_width=True)
    else:
        st.warning("No hay datos para el rango de fechas seleccionado.")

with col_der:
    st.subheader("🏷️ Ventas por Categoría")
    df_categorias = get_ventas_por_categoria()
    
    if not df_categorias.empty:
        fig_categorias = grafico_categorias(df_categorias)
        st.plotly_chart(fig_categorias, use_container_width=True)
    else:
        st.warning("No hay datos de categorías disponibles.")

st.markdown("---")

# ============================================
# GRÁFICOS - FILA 2
# ============================================
col_izq2, col_der2 = st.columns(2)

with col_izq2:
    st.subheader("🏆 Top 10 Productos")
    df_productos = get_productos_mas_vendidos(10)
    
    if not df_productos.empty:
        fig_productos = grafico_productos_top(df_productos)
        st.plotly_chart(fig_productos, use_container_width=True)
    else:
        st.warning("No hay datos de productos disponibles.")

with col_der2:
    st.subheader("👤 Ventas por Usuario")
    df_usuarios = get_ventas_por_usuario()
    
    if not df_usuarios.empty:
        fig_usuarios = grafico_ventas_usuario(df_usuarios)
        st.plotly_chart(fig_usuarios, use_container_width=True)
    else:
        st.warning("No hay datos de usuarios disponibles.")

st.markdown("---")

# ============================================
# TABLAS DE DATOS
# ============================================
st.subheader("📋 Detalle de Datos")

tab1, tab2, tab3 = st.tabs(["Por Fecha", "Por Categoría", "Por Tipo de Salida"])

with tab1:
    if not df_ventas_fecha.empty:
        st.dataframe(df_ventas_fecha, use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

with tab2:
    if not df_categorias.empty:
        st.dataframe(df_categorias, use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

with tab3:
    df_tipo_salida = get_ventas_por_tipo_salida()
    if not df_tipo_salida.empty:
        st.dataframe(df_tipo_salida, use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

# ============================================
# PIE DE PÁGINA
# ============================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Dashboard de Ventas | Desarrollado con Python, Streamlit y MySQL
    </div>
    """,
    unsafe_allow_html=True
)
```

---

## FASE 8: Ejecutar el Dashboard

### Paso 8.1: Verificar que el entorno está activo

Tu terminal debe mostrar:
```
(.venv) PS C:\Users\Bernardo\Desktop\dashboard_ventas>
```

Si no, actívalo:
```powershell
.\.venv\Scripts\Activate
```

---

### Paso 8.2: Ejecutar la aplicación

```powershell
streamlit run app.py
```

**Resultado esperado:**
- Se abrirá automáticamente tu navegador
- Verás el dashboard en `http://localhost:8501`

---

### Paso 8.3: Detener la aplicación

Para detener el servidor de Streamlit:
- Presiona `Ctrl + C` en la terminal

---

## FASE 9: Estructura Final del Proyecto

```
dashboard_ventas/
│
├── .venv/                      # Entorno virtual (ignorado por Git)
├── .git/                       # Carpeta de control de versiones
│
├── config/
│   └── database.py             # Conexión a MySQL
│
├── data/
│   └── queries.py              # Consultas SQL
│
├── components/
│   └── charts.py               # Gráficos con Plotly
│
├── .env                        # Credenciales (NO subir a Git)
├── .gitignore                  # Archivos ignorados por Git
├── requirements.txt            # Dependencias del proyecto
├── test_connection.py          # Script de prueba de conexión
└── app.py                      # Aplicación principal
```

---

## FASE 10: Control de Versiones con Git y GitHub

### Paso 10.1: Verificar que Git está instalado

```powershell
git --version
```

**Resultado esperado:**
```
git version 2.44.0.windows.1
```

---

### Paso 10.2: Configurar Git (solo la primera vez)

Si nunca has configurado Git, ejecuta estos comandos con tus datos:

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo@ejemplo.com"
```

---

### Paso 10.3: Inicializar el repositorio local

Desde la carpeta del proyecto:

```powershell
git init
```

---

### Paso 10.4: Agregar archivos y hacer el primer commit

```powershell
# Agregar todos los archivos (respetando .gitignore)
git add .

# Crear el primer commit
git commit -m "Primer commit: Dashboard de ventas inicial"
```

---

### Paso 10.5: Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) e inicia sesión
2. Clic en el botón **"New"** (o **"+"** → **"New repository"**)
3. Configura el repositorio:
   - **Repository name:** `dashback` (o el nombre que prefieras)
   - **Description:** Dashboard de ventas con Python, Streamlit y MySQL
   - **Visibilidad:** Public o Private (según tu preferencia)
   - **NO marques** "Add a README file"
   - **NO selecciones** .gitignore ni license
4. Clic en **"Create repository"**

---

### Paso 10.6: Conectar el repositorio local con GitHub

Ejecuta estos comandos en la terminal (reemplaza la URL con la de tu repositorio):

```powershell
# Conectar con el repositorio remoto
git remote add origin https://github.com/tu_usuario/tu_repositorio.git

# Renombrar la rama principal a "main"
git branch -M main

# Subir el código a GitHub
git push -u origin main
```

**Resultado esperado:**
```
Enumerating objects: 13, done.
Counting objects: 100% (13/13), done.
Delta compression using up to 8 threads
Compressing objects: 100% (10/10), done.
Writing objects: 100% (13/13), 10.16 KiB | 2.03 MiB/s, done.
Total 13 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
To https://github.com/tu_usuario/tu_repositorio.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

---

### Paso 10.7: Flujo de trabajo diario con Git

Cada vez que hagas cambios en tu proyecto, sigue este flujo:

```powershell
# 1. Ver qué archivos han cambiado
git status

# 2. Agregar los cambios
git add .

# 3. Crear un commit con un mensaje descriptivo
git commit -m "Descripción breve de los cambios realizados"

# 4. Subir los cambios a GitHub
git push
```

> **💡 Tip:** Escribe mensajes de commit descriptivos. Por ejemplo:
> - `"Agregar filtro por categoría en dashboard"`
> - `"Corregir error en consulta de ventas por fecha"`
> - `"Añadir gráfico de tendencias mensuales"`

---

## COMANDOS DE REFERENCIA RÁPIDA

| Acción | Comando |
|--------|---------|
| Activar entorno virtual | `.\.venv\Scripts\Activate` |
| Desactivar entorno virtual | `deactivate` |
| Instalar dependencias | `pip install -r requirements.txt` |
| Ejecutar dashboard | `streamlit run app.py` |
| Detener dashboard | `Ctrl + C` |
| Ver paquetes instalados | `pip list` |
| Guardar dependencias | `pip freeze > requirements.txt` |
| Ver estado de Git | `git status` |
| Agregar cambios | `git add .` |
| Crear commit | `git commit -m "mensaje"` |
| Subir a GitHub | `git push` |
| Descargar cambios | `git pull` |

---

## PRÓXIMOS PASOS (Mejoras Futuras)

1. **Agregar más vistas SQL** de tu base de datos para enriquecer el dashboard
2. **Implementar caché** con `@st.cache_data` para mejorar rendimiento
3. **Agregar autenticación** para proteger el acceso al dashboard
4. **Crear páginas múltiples** usando `st.Page` de Streamlit
5. **Agregar exportación a Excel/PDF** de los reportes
6. **Implementar filtros dinámicos** por categoría, usuario, tipo de salida

---

## SOLUCIÓN DE PROBLEMAS COMUNES

### Error: "No module named 'config'"
**Solución:** Asegúrate de estar ejecutando desde la raíz del proyecto y que exista el archivo `config/__init__.py` (créalo vacío si no existe).

### Error: "Access denied for user"
**Solución:** Verifica las credenciales en el archivo `.env`

### Error: "mysql.connector not found"
**Solución:** Activa el entorno virtual y ejecuta `pip install mysql-connector-python`

### El dashboard no muestra datos
**Solución:** 
1. Ejecuta `python test_connection.py` para verificar la conexión
2. Verifica que la vista `comandas_v6_base` exista en la base de datos
3. Revisa que haya datos en la vista

---

**¡Listo!** 🎉 Siguiendo esta guía tendrás un dashboard funcional de ventas.
