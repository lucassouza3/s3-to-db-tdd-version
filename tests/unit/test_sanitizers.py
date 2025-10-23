import pytest

from infra.sanitizers import sanitize_text, parse_date, normalize_sex


def test_sanitize_text_removes_accents_and_whitespace():
    assert sanitize_text(" Jo\u00E3o  da   Silva ") == "JOAO DA SILVA"


def test_parse_date_accepts_multiple_formats():
    assert str(parse_date("19870115")) == "1987-01-15"
    assert str(parse_date("15/01/1987")) == "1987-01-15"
    assert parse_date("INVALID") is None


def test_normalize_sex_maps_codes_to_letters():
    assert normalize_sex("1") == "M"
    assert normalize_sex("2") == "F"
    assert normalize_sex("3") == "U"

