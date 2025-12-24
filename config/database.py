from __future__ import annotations

import os
from dataclasses import dataclass

import mysql.connector
from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    ssl_disabled: bool = True


def get_database_settings() -> DatabaseSettings:
    """Lee la configuración de MySQL desde variables de entorno (.env)."""
    load_dotenv(override=False)

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "")

    ssl_disabled_raw = os.getenv("DB_SSL_DISABLED", "true").strip().lower()
    ssl_disabled = ssl_disabled_raw in {"1", "true", "yes", "y"}

    return DatabaseSettings(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        ssl_disabled=ssl_disabled,
    )


def get_connection():
    """Crea una conexión nueva a MySQL usando mysql-connector-python."""
    settings = get_database_settings()

    if not settings.database:
        raise ValueError(
            "DB_NAME está vacío. Configúralo en el archivo .env antes de conectar."
        )

    connect_kwargs: dict = {
        "host": settings.host,
        "port": settings.port,
        "user": settings.user,
        "password": settings.password,
        "database": settings.database,
    }

    if settings.ssl_disabled:
        connect_kwargs["ssl_disabled"] = True

    return mysql.connector.connect(**connect_kwargs)
