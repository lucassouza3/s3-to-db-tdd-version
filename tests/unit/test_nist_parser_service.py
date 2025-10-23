from __future__ import annotations

from project.application.services.nist_parser_service import (
    NistParserService,
    OriginBase,
    Person,
)


def test_parse_returns_entities_with_sanitized_origin() -> None:
    raw = b"1:008 TSe \n"
    parser = NistParserService()

    person, origin_base = parser.parse(raw)

    assert isinstance(person, Person)
    assert isinstance(origin_base, OriginBase)
    assert origin_base.origin == "TSE"


def test_parse_defaults_when_origin_missing() -> None:
    parser = NistParserService()

    _, origin_base = parser.parse(b"no markers here")

    assert origin_base.origin == "UNKNOWN"


def test_compose_key_for_upload_builds_path() -> None:
    raw = b"1:008 TSE\n"
    parser = NistParserService()

    key = parser.compose_key_for_upload("116908146.nst", raw)

    assert key == "nist/TSE/116908146.nst"


def test_destination_key_for_processed_uses_filename_from_source_key() -> None:
    raw = b"1:008 TSE\n"
    parser = NistParserService()

    destination = parser.destination_key_for_processed("some/prefix/116908146.nst", raw)

    assert destination == "nist-lidos/TSE/116908146.nst"


def test_destination_key_for_processed_handles_missing_marker() -> None:
    parser = NistParserService()

    destination = parser.destination_key_for_processed("some/prefix/116908146.nst", b"no markers")

    assert destination == "nist-lidos/unknown/116908146.nst"
