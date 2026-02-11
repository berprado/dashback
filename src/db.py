from __future__ import annotations

from typing import cast
import logging

import streamlit as st
from streamlit.connections.sql_connection import SQLConnection


CONNECTION_SCOPE: str | None = "session"


def _cleanup_connection(conn: SQLConnection) -> None:
    """Callback para liberar recursos al cerrar sesión."""
    try:
        logging.info("Liberando conexión SQL: %s", conn)
    except Exception:
        pass


@st.cache_resource(show_spinner=False, scope=CONNECTION_SCOPE, on_release=_cleanup_connection)
def get_connection(connection_name: str = "mysql") -> SQLConnection:
    """Devuelve la conexión MySQL configurada en `.streamlit/secrets.toml`.

    Requiere que exista un bloque como:

    [connections.mysql]
    type = "sql"
    url = "mysql+mysqlconnector://user:pass@host:3306/db"

    Para producción, se puede definir adicionalmente:

    [connections.mysql_prod]
    type = "sql"
    url = "mysql+mysqlconnector://user:pass@host:3306/db"
    """

    return cast(SQLConnection, st.connection(connection_name, type="sql"))


def validate_connection(conn: SQLConnection) -> bool:
    """Valida que la conexión esté activa."""
    try:
        from src.query_store import fetch_dataframe
        df = fetch_dataframe(conn, "SELECT 1 AS ping", ttl=0)
        return df is not None and not df.empty
    except Exception:
        return False
