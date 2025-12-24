from __future__ import annotations

from typing import cast

import streamlit as st
from streamlit.connections.sql_connection import SQLConnection


@st.cache_resource(show_spinner=False)
def get_connection() -> SQLConnection:
    """Devuelve la conexión MySQL configurada en `.streamlit/secrets.toml`.

    Requiere que exista un bloque como:

    [connections.mysql]
    type = "sql"
    url = "mysql+mysqlconnector://user:pass@host:3306/db"
    """

    return cast(SQLConnection, st.connection("mysql", type="sql"))
