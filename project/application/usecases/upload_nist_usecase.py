from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class UploadNistUseCase:
    """Caso de uso para realizar o upload de um arquivo .nst local."""

    s3: "S3Port"
    nist_tools: "NistParserService"

    def execute(self, file_path: str) -> str:
        """Le um arquivo local, gera a chave S3 e envia o conteudo para o bucket."""
        path = Path(file_path)
        raw = path.read_bytes()
        key = self.nist_tools.compose_key_for_upload(path.name, raw)
        self.s3.upload_bytes(key, raw)
        return key
