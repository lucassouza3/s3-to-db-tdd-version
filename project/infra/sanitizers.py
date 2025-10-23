from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional


def sanitize_text(value: Optional[str]) -> str:
    """Remove acentos, normaliza espacos e retorna a string em maiusculas."""
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    single_spaced = re.sub(r"\s+", " ", without_accents)
    return single_spaced.strip().upper()


_DATE_FORMATS = (
    "%Y%m%d",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
)


def parse_date(value: Optional[str]) -> Optional[date]:
    """Interpreta datas em multiplos formatos, retornando date ou None."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_sex(value: Optional[str]) -> str:
    """Normaliza codigos de sexo para 'M', 'F' ou 'U'."""
    if value is None:
        return "U"

    text = str(value).strip().upper()
    if text in {"M", "MALE", "MASC", "MASCULINO"}:
        return "M"
    if text in {"F", "FEMALE", "FEM", "FEMININO"}:
        return "F"

    if text == "1":
        return "M"
    if text == "2":
        return "F"

    return "U"
