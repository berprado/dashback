# Dashback

Dashboard operativo en **Streamlit** conectado a **MySQL 5.6**.

## Requisitos
- Python 3.10+
- Streamlit 1.52.2

## Configuración de conexión
1. Copia el ejemplo:
   - `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
2. Edita el `url` según tu entorno.

## Ejecutar
- `streamlit run app.py`

## Estructura
- `app.py`: entrypoint Streamlit
- `src/db.py`: conexión vía Streamlit Connections (`st.connection`)
- `src/query_store.py`: queries (`Q_...`) + `fetch_dataframe`
- `src/ui/`: layout y componentes UI
- `docs/`: documentos de referencia de negocio
