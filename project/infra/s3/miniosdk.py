from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from minio import Minio
import urllib3

from project.config import Config


@dataclass(frozen=True)
class MinioFactory:
    """Fábrica para construir clientes MinIO a partir de Config.

    Exemplo
    >>> from project.config import load_config
    >>> cfg = load_config()
    >>> client = MinioFactory(cfg).build()
    >>> isinstance(client, Minio)
    True
    """

    config: Config

    def build(self) -> Minio:
        """Cria um cliente MinIO com timeouts padrão (5s conexão/leitura).

        Exemplo
        >>> from project.config import load_config
        >>> cfg = load_config()
        >>> MinioFactory(cfg).build()  # doctest: +ELLIPSIS
        <minio.api.Minio object at ...>
        """
        endpoint = self.config.s3_endpoint.replace("http://", "").replace("https://", "")
        http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5.0, read=5.0))
        return Minio(
            endpoint=endpoint,
            access_key=self.config.s3_access,
            secret_key=self.config.s3_secret,
            secure=self.config.s3_secure,
            http_client=http,
        )
