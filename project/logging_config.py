from __future__ import annotations

import logging
import os


def setup_logging(level: str | None = None) -> None:
    """Configura logging básico para a aplicação.

    Exemplo
    >>> setup_logging('DEBUG')
    >>> logging.getLogger(__name__).debug('mensagem de debug')
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
