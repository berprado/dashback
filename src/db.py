from __future__ import annotations

from typing import cast

import streamlit as st
from streamlit.connections.sql_connection import SQLConnection


@st.cache_resource(show_spinner=False)
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
