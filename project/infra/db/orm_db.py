from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psycopg

from project.config import Config


@dataclass
class PgManager:
    """Gerencia conexões PostgreSQL (psycopg).

    Exemplo
    >>> from project.config import load_config
    >>> cfg = load_config()
    >>> pg = PgManager(cfg)
    >>> isinstance(pg.test_connection(), str)  # doctest: +SKIP
    True
    """
    config: Config

    def connect(self) -> psycopg.Connection:
        """Abre uma conexão com os parâmetros do .env/Config."""
        return psycopg.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            dbname=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password,
        )

    def test_connection(self) -> str:
        """Executa `SELECT version()` para validar a conexão."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version: str = cur.fetchone()[0]
        return version
