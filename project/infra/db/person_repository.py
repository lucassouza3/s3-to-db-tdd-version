from __future__ import annotations

from dataclasses import dataclass

import psycopg

from project.application.ports.repository_port import RepositoryPort
from project.config import Config


@dataclass
class PgPersonRepository(RepositoryPort):
    """Repositório PostgreSQL responsável por inserir e registrar dados provenientes dos NISTs."""

    config: Config

    def _connect(self) -> psycopg.Connection:
        """Abre uma conexão com PostgreSQL utilizando as credenciais da configuração."""
        return psycopg.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            dbname=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password,
        )

    def _ensure_schema(self, cursor: psycopg.Cursor) -> None:
        """Garante a existência de schema, tabelas e restrições necessárias."""
        cursor.execute("CREATE SCHEMA IF NOT EXISTS findface;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS findface.tb_nist_ingest (
                id BIGSERIAL PRIMARY KEY
            );
            """
        )
        cursor.execute("ALTER TABLE findface.tb_nist_ingest ADD COLUMN IF NOT EXISTS s3_key TEXT;")
        cursor.execute("ALTER TABLE findface.tb_nist_ingest ADD COLUMN IF NOT EXISTS md5_hash TEXT;")
        cursor.execute("ALTER TABLE findface.tb_nist_ingest ADD COLUMN IF NOT EXISTS origin TEXT;")
        cursor.execute(
            """
            ALTER TABLE findface.tb_nist_ingest
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """
        )

        cursor.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_tb_nist_ingest_md5'
                ) THEN
                    ALTER TABLE findface.tb_nist_ingest
                    ADD CONSTRAINT uq_tb_nist_ingest_md5 UNIQUE (md5_hash);
                END IF;
            END $$;
            """
        )
        cursor.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_tb_nist_ingest_s3key'
                ) THEN
                    ALTER TABLE findface.tb_nist_ingest
                    ADD CONSTRAINT uq_tb_nist_ingest_s3key UNIQUE (s3_key);
                END IF;
            END $$;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS findface.tb_log (
                id BIGSERIAL PRIMARY KEY,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

    def upsert_person_from_nist(self, person: object, origin_base: object, md5_hash: str) -> None:
        """Executa upsert em findface.tb_nist_ingest identificando registros pelo md5."""
        s3_key = getattr(person, "s3_key", None) or getattr(origin_base, "s3_key", None)
        origin = getattr(origin_base, "origin", None)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._ensure_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO findface.tb_nist_ingest (s3_key, md5_hash, origin)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (md5_hash) DO UPDATE SET origin = EXCLUDED.origin
                    """,
                    (s3_key, md5_hash, origin),
                )

    def log(self, level: str, message: str) -> None:
        """Registra entradas de log na tabela findface.tb_log."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._ensure_schema(cursor)
                cursor.execute(
                    "INSERT INTO findface.tb_log (level, message) VALUES (%s, %s)",
                    (level, message),
                )
