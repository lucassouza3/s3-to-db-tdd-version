from __future__ import annotations

from typing import Protocol, Sequence


class S3Port(Protocol):
    """Porta de acesso ao S3/MinIO utilizada pela camada de aplicacao."""

    def list_nists(self) -> Sequence[str]:
        """Lista chaves com sufixo .nst sob o prefixo 'nist/'."""
        ...

    def read_bytes(self, key: str) -> bytes:
        """Le bytes de uma chave do bucket."""
        ...

    def move_processed(self, key: str, dest_key: str) -> None:
        """Move um objeto (copia e remove) para a chave de destino."""
        ...

    def upload_bytes(self, key: str, raw: bytes) -> None:
        """Envia bytes para a chave informada."""
        ...

    def object_exists(self, key: str) -> bool:
        """Retorna True se o objeto existir no bucket."""
        ...

    def delete_object(self, key: str) -> None:
        """Remove um objeto específico do bucket."""
        ...

    def delete_prefix(self, prefix: str) -> int:
        """Remove todos os objetos que iniciam com o prefixo informado e retorna o total removido."""
        ...
