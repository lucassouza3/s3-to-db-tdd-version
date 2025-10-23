from __future__ import annotations

from typing import Protocol


class RepositoryPort(Protocol):
    """Porta de persistencia e logs utilizada pela camada de aplicacao."""

    def upsert_person_from_nist(self, person: object, origin_base: object, md5_hash: str) -> None:
        """Persiste ou atualiza dados derivados do NIST com base no md5."""
        ...

    def log(self, level: str, message: str) -> None:
        """Registra mensagens de log relacionadas ao processamento."""
        ...
