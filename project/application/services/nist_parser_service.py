from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from project.infra.sanitizers import sanitize_text
from project.infra.s3.s3_manager import _field_1_008


@dataclass
class Person:
    """Entidade de dominio (simplificada) para representar uma pessoa."""

    name: str | None = None
    document: str | None = None
    sex: str | None = None
    birth_date: str | None = None  # simplificado


@dataclass
class OriginBase:
    """Entidade de dominio (simplificada) que guarda a origem do NIST."""

    origin: str | None = None


@dataclass
class NistParserService:
    """Servico de parsing NIST (versao inicial e heuristica)."""

    def parse(self, raw: bytes) -> Tuple[Person, OriginBase]:
        """Extrai entidades a partir do payload NIST.

        Implementacao simplificada: apenas origem (1:008), normalizada.
        """
        origin_value = _field_1_008(raw) or "unknown"
        person = Person()
        origin_base = OriginBase(origin=sanitize_text(origin_value))
        return person, origin_base

    def compose_key_for_upload(self, filename: str, raw: bytes) -> str:
        """Monta a chave S3 no padrao 'nist/<1:008>/<arquivo>.nst'."""
        origin_value = _field_1_008(raw) or "unknown"
        return f"nist/{origin_value}/{filename}"

    def destination_key_for_processed(self, key: str, raw: bytes) -> str:
        """Gera a chave de destino de arquivos processados sob 'nist-lidos/'."""
        origin_value = _field_1_008(raw) or "unknown"
        parts = key.split("/")
        filename = parts[-1] if parts else key
        return f"nist-lidos/{origin_value}/{filename}"
