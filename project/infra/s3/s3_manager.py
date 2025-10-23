from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error

from project.application.ports.s3_port import S3Port

_CONTROL_SEPARATORS = ("\x1d", "\x1e", "\x1f")


def _sanitize_text_payload(nist_bytes: bytes) -> str:
    """Decodifica o payload NIST para texto substituindo separadores de controle por quebras de linha."""
    text = nist_bytes.decode("latin-1", errors="ignore")
    for sep in _CONTROL_SEPARATORS:
        text = text.replace(sep, "\n")
    return text


def _tag_matches(tag: str, type_no: int, field_no: int) -> bool:
    """Verifica se uma tag (ex.: 1:008, 1.08, 1.0008) corresponde ao campo desejado."""
    digits = "".join(ch for ch in tag if ch.isdigit())
    if not digits:
        return False
    digits = digits.lstrip("0") or "0"
    type_digits = str(type_no)
    if not digits.startswith(type_digits):
        return False
    field_digits = digits[len(type_digits) :] or "0"
    field_value = field_digits.lstrip("0") or "0"
    try:
        return int(field_value) == field_no
    except ValueError:
        return False


def _extract_field(nist_bytes: bytes, type_no: int, field_no: int) -> Optional[str]:
    """Localiza um campo NIST tolerando variantes como 1:008, 1.08, 1.0008."""
    if not nist_bytes:
        return None

    text = _sanitize_text_payload(nist_bytes)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^\s*([0-9][0-9\s:.\-]*[0-9])\s*[:=\-]?\s*(.*)$", line)
        if not match:
            continue
        tag, value = match.group(1), match.group(2)
        if _tag_matches(tag, type_no, field_no):
            cleaned = value.strip(" \t\r\n|;,")
            return cleaned or None
    return None


def _field_1_008(nist_bytes: bytes) -> Optional[str]:
    """Extrai o campo 1:008 (origem) do payload NIST, aceitando variações de formato.

    Exemplo
    >>> _field_1_008(b"1:008 TSE\\n1:009 123")
    'TSE'
    >>> _field_1_008(b"1.08:TSE")
    'TSE'
    >>> _field_1_008(b"1.0008=TSE")
    'TSE'
    >>> _field_1_008(b'sem tag aqui') is None
    True
    """
    return _extract_field(nist_bytes, type_no=1, field_no=8)


@dataclass
class MinioS3Adapter(S3Port):
    """Adaptador S3 baseado em MinIO que implementa o contrato S3Port."""

    client: Minio
    bucket: str

    def list_nists(self) -> Sequence[str]:
        """Retorna chaves do S3 sob nist/ terminadas com .nst."""
        objs = self.client.list_objects(self.bucket, prefix="nist/", recursive=True)
        keys: list[str] = []
        for obj in objs:
            key = getattr(obj, "object_name", None) or getattr(obj, "object_name", "")
            if key.endswith(".nst"):
                keys.append(key)
        return keys

    def read_bytes(self, key: str) -> bytes:
        """Lê bytes brutos de um objeto no S3."""
        resp = self.client.get_object(self.bucket, key)
        try:
            data = resp.read()
        finally:
            resp.close()
            resp.release_conn()
        return data

    def move_processed(self, key: str, dest_key: str) -> None:
        """Move um objeto realizando cópia e, na sequência, removendo a origem."""
        self.client.copy_object(self.bucket, dest_key, CopySource(self.bucket, key))
        self.client.remove_object(self.bucket, key)

    def upload_bytes(self, key: str, raw: bytes) -> None:
        """Envia bytes para a chave informada."""
        self.client.put_object(self.bucket, key, data=raw, length=len(raw))

    def object_exists(self, key: str) -> bool:
        """Retorna True se o objeto existir no bucket."""
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False

    def delete_object(self, key: str) -> None:
        """Remove um objeto específico do bucket."""
        self.client.remove_object(self.bucket, key)

    def delete_prefix(self, prefix: str) -> int:
        """Remove todos os objetos que começam com o prefixo informado."""
        removed = 0
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        for obj in objects:
            key = getattr(obj, "object_name", None) or getattr(obj, "object_name", "")
            self.client.remove_object(self.bucket, key)
            removed += 1
        return removed
