from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5


@dataclass
class ChecksumService:
    """Servico responsavel pelo calculo de checksums."""

    def md5_bytes(self, data: bytes) -> str:
        """Calcula o hash MD5 (hex) para um buffer de bytes."""
        return md5(data).hexdigest()
