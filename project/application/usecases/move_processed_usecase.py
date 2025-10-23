from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MoveProcessedUseCase:
    """Caso de uso para mover um objeto processado para 'nist-lidos/'."""

    s3: "S3Port"
    nist_tools: "NistParserService"

    def execute(self, key: str, raw: bytes) -> str:
        """Calcula a chave de destino e realiza a movimentacao no S3."""
        destination = self.nist_tools.destination_key_for_processed(key, raw)
        self.s3.move_processed(key, destination)
        return destination
