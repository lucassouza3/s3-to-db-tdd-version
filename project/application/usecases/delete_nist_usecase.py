from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeleteNistUseCase:
    """Caso de uso para remover objetos NIST do bucket S3."""

    s3: "S3Port"

    def delete_by_key(self, key: str) -> None:
        """Remove um objeto específico identificado pela chave completa."""
        self.s3.delete_object(key)

    def delete_by_prefix(self, prefix: str) -> int:
        """Remove todos os objetos que iniciam com o prefixo informado e retorna o total removido."""
        return self.s3.delete_prefix(prefix)

    def delete_all(self) -> int:
        """Remove todos os objetos do bucket."""
        return self.s3.delete_prefix("")
