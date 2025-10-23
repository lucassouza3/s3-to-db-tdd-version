from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class S3Port(Protocol):
    """Porta S3 utilizada pelo caso de uso de processamento."""

    def list_nists(self) -> Sequence[str]:
        """Lista chaves candidatas para processamento."""
        ...

    def read_bytes(self, key: str) -> bytes:
        """Lê o conteúdo bruto de um objeto S3."""
        ...

    def move_processed(self, key: str, dest_key: str) -> None:
        """Move um objeto processado para a chave de destino."""
        ...


class RepositoryPort(Protocol):
    """Porta de repositório para persistência e logs."""

    def upsert_person_from_nist(self, person: object, origin_base: object, md5_hash: str) -> None:
        """Persiste ou atualiza os dados derivados do NIST."""
        ...

    def log(self, level: str, message: str) -> None:
        """Registra mensagens de log."""
        ...


@dataclass
class ProcessNistUseCase:
    """Processa os NISTs pendentes disponíveis no bucket."""

    s3: S3Port
    repository: RepositoryPort
    parser: "NistParserService"
    checksum: "ChecksumService"

    def execute(self) -> int:
        """Executa o fluxo de processamento e retorna a quantidade de itens tratados."""
        processed = 0
        for key in self.s3.list_nists():
            try:
                raw = self.s3.read_bytes(key)
                md5_hash = self.checksum.md5_bytes(raw)
                person, origin_base = self.parser.parse(raw)

                # Acrescenta metadados mínimos para persistência.
                try:
                    setattr(origin_base, "s3_key", key)
                except Exception:
                    pass

                self.repository.upsert_person_from_nist(person, origin_base, md5_hash)

                destination = self.parser.destination_key_for_processed(key, raw)
                self.s3.move_processed(key, destination)
                self.repository.log("INFO", f"Processed {key} -> {destination}")
                processed += 1
            except Exception as exc:  # pragma: no cover - dependência externa
                self.repository.log("ERROR", f"Failed {key}: {exc}")
        return processed
