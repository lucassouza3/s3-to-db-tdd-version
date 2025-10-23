from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys


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
    s3_access = _prompt_credential(
        cache_key="s3_access",
        prompt="Usuário do S3",
        env_name="S3_ACCESS",
        default=os.getenv("S3_ACCESS", "minio"),
        mask=False,
    )
    s3_secret = _prompt_credential(
        cache_key="s3_secret",
        prompt="Senha do S3",
        env_name="S3_SECRET",
        default=os.getenv("S3_SECRET"),
        mask=True,
    )
    db_user = _prompt_credential(
        cache_key="db_user",
        prompt="Usuário do banco de dados",
        env_name="DB_USER",
        default=os.getenv("DB_USER", "postgres"),
        mask=False,
    )
    db_password = _prompt_credential(
        cache_key="db_password",
        prompt="Senha do banco de dados",
        env_name="DB_PASSWORD",
        default=os.getenv("DB_PASSWORD"),
        mask=True,
    )

    return Config(
        s3_endpoint=os.getenv("S3_ENDPOINT", "http://127.0.0.1:9000"),
        s3_bucket=os.getenv("S3_BUCKET", "teste"),
        s3_access=s3_access,
        s3_secret=s3_secret,
        s3_secure=_getenv_bool("S3_SECURE", False),
        db_host=_getenv_first(["DB_HOST", "PG_HOST"], "127.0.0.1"),
        db_port=int(_getenv_first(["DB_PORT", "PG_PORT"], "5432")),
        db_name=_getenv_first(["DB_NAME", "PG_DB"], "mitra"),
        db_user=db_user,
        db_password=db_password,
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


_PROMPT_CACHE: dict[str, str] = {}


def _prompt_credential(
    cache_key: str,
    prompt: str,
    env_name: Optional[str],
    default: Optional[str],
    mask: bool,
) -> str:
    if cache_key in _PROMPT_CACHE:
        return _PROMPT_CACHE[cache_key]

    env_value = os.getenv(env_name) if env_name else None
    base_default = env_value if env_value else default

    value = _interactive_prompt(prompt, base_default, mask)
    if env_name:
        os.environ[env_name] = value
    _PROMPT_CACHE[cache_key] = value
    return value


def _interactive_prompt(prompt: str, default: Optional[str], mask: bool) -> str:
    if not sys.stdin.isatty():
        if default is not None:
            return default
        raise RuntimeError(
            f"Entrada requerida para '{prompt}', mas o modo não-interativo não permite coleta. "
            "Defina as variáveis de ambiente apropriadas para execução automatizada."
        )

    if mask:
        return _prompt_secret(prompt, default)
    return _prompt_text(prompt, default)


def _prompt_text(prompt: str, default: Optional[str]) -> str:
    label = prompt
    if default:
        label += f" [{default}]"
    label += ": "
    while True:
        value = input(label).strip()
        if value:
            return value
        if default:
            return default
        print("Valor obrigatório. Tente novamente.")


def _prompt_secret(prompt: str, default: Optional[str]) -> str:
    hint = " (pressione Enter para manter o valor configurado)" if default else ""
    label = f"{prompt}{hint}: "
    while True:
        value = _masked_input(label)
        if value:
            return value
        if default:
            return default
        print("Valor obrigatório. Tente novamente.")


def _masked_input(prompt: str) -> str:
    try:
        import msvcrt  # type: ignore[attr-defined]

        print(prompt, end="", flush=True)
        buffer: list[str] = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                print()
                break
            if ch == "\003":  # Ctrl+C
                raise KeyboardInterrupt
            if ch == "\b":
                if buffer:
                    buffer.pop()
                    print("\b \b", end="", flush=True)
                continue
            buffer.append(ch)
            print("*", end="", flush=True)
        return "".join(buffer)
    except ImportError:
        pass

    # POSIX fallback
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        buffer: list[str] = []
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\n", "\r"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            if ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            if ch in ("\x7f", "\b"):
                if buffer:
                    buffer.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            buffer.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
        return "".join(buffer)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
