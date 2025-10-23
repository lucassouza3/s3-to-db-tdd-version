from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Configuração da aplicação carregada do ambiente/.env.

    Exemplo
    >>> from project.config import load_config
    >>> cfg = load_config()
    >>> hasattr(cfg, 's3_endpoint') and hasattr(cfg, 'db_host')
    True
    """
    s3_endpoint: str
    s3_bucket: str
    s3_access: str
    s3_secret: str
    s3_secure: bool

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    log_level: str


def _getenv_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y"}


def load_config() -> Config:
    """Carrega a configuração (lendo .env se presente).

    Exemplo
    >>> cfg = load_config()
    >>> isinstance(cfg.s3_secure, bool)
    True
    """
    _load_env_file()
    return Config(
        s3_endpoint=os.getenv("S3_ENDPOINT", "http://127.0.0.1:9000"),
        s3_bucket=os.getenv("S3_BUCKET", "teste"),
        s3_access=os.getenv("S3_ACCESS", "minio"),
        s3_secret=os.getenv("S3_SECRET", "minio123"),
        s3_secure=_getenv_bool("S3_SECURE", False),
        db_host=_getenv_first(["DB_HOST", "PG_HOST"], "127.0.0.1"),
        db_port=int(_getenv_first(["DB_PORT", "PG_PORT"], "5432")),
        db_name=_getenv_first(["DB_NAME", "PG_DB"], "mitra"),
        db_user=_getenv_first(["DB_USER", "PG_USER"], "postgres"),
        db_password=_getenv_first(["DB_PASSWORD", "PG_PASSWORD"], "postgres"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def _load_env_file(filename: str = ".env") -> None:
    """Carrega variáveis de um arquivo .env simples (KEY=VALUE).

    Exemplo
    >>> _load_env_file()  # silencioso quando não existe
    """
    root = Path(__file__).resolve().parents[1]
    env_path = root / filename
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            # Remove potencial BOM no início do arquivo
            if line and line[0] == "\ufeff":
                line = line.lstrip("\ufeff")
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            # Sobrescreve o ambiente para garantir uso do .env
            if k:
                os.environ[k] = v
    except Exception:
        # carregamento best-effort; em caso de erro, ignora
        pass


def _getenv_first(names: list[str], default: str) -> str:
    """Retorna o primeiro valor não vazio entre variáveis possíveis.

    Exemplo
    >>> _getenv_first(['__NOTSET__'], 'x')
    'x'
    """
    for n in names:
        v = os.getenv(n)
        if v is not None and v != "":
            return v
    return default
