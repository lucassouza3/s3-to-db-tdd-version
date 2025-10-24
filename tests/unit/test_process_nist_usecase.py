from __future__ import annotations

from dataclasses import dataclass

from project.application.services.nist_parser_service import OriginBase, Person
from project.application.usecases.process_nist_usecase import ProcessNistUseCase


class DummyS3:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.moves: list[tuple[str, str]] = []
        self.keys = ["nist/TSE/sample.nst"]
        self.read_calls: list[str] = []

    def list_nists(self) -> list[str]:
        return list(self.keys)

    def read_bytes(self, key: str) -> bytes:
        self.read_calls.append(key)
        return self.payload

    def move_processed(self, key: str, dest: str) -> None:
        self.moves.append((key, dest))


class DummyChecksum:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    def md5_bytes(self, data: bytes) -> str:
        self.calls.append(data)
        return f"md5-{len(data)}"


@dataclass
class DummyRepository:
    upsert_calls: list[tuple[object, object, str]]
    log_calls: list[tuple[str, str]]

    def upsert_person_from_nist(self, person: object, origin_base: object, md5_hash: str) -> None:
        self.upsert_calls.append((person, origin_base, md5_hash))

    def log(self, level: str, message: str) -> None:
        self.log_calls.append((level, message))


class DummyParser:
    def parse(self, raw: bytes) -> tuple[Person, OriginBase]:
        origin = OriginBase(origin="TSE")
        return Person(), origin

    def destination_key_for_processed(self, key: str, raw: bytes) -> str:  # noqa: ARG002
        return f"nist-lidos/TSE/{key.split('/')[-1]}"


def test_execute_processes_each_key_and_moves_to_destination() -> None:
    payload = b"1:008 TSE\n"
    s3 = DummyS3(payload=payload)
    checksum = DummyChecksum()
    repository = DummyRepository(upsert_calls=[], log_calls=[])
    parser = DummyParser()
    usecase = ProcessNistUseCase(s3=s3, repository=repository, parser=parser, checksum=checksum)

    processed = usecase.execute()

    assert processed == 1
    assert s3.read_calls == ["nist/TSE/sample.nst"]
    assert checksum.calls == [payload]
    assert len(repository.upsert_calls) == 1
    person, origin_base, md5_hash = repository.upsert_calls[0]
    assert isinstance(person, Person)
    assert isinstance(origin_base, OriginBase)
    assert getattr(origin_base, "s3_key") == "nist/TSE/sample.nst"
    assert md5_hash == "md5-10"
    assert s3.moves == [("nist/TSE/sample.nst", "nist-lidos/TSE/sample.nst")]
    assert ("INFO", "Processed nist/TSE/sample.nst -> nist-lidos/TSE/sample.nst") in repository.log_calls


def test_execute_logs_errors_and_continues() -> None:
    payload = b"1:008 TSE\n"
    checksum = DummyChecksum()
    repository = DummyRepository(upsert_calls=[], log_calls=[])
    parser = DummyParser()

    class FlakyS3(DummyS3):
        def list_nists(self) -> list[str]:
            return ["nist/TSE/fail.nst", "nist/TSE/ok.nst"]

        def read_bytes(self, key: str) -> bytes:
            if key.endswith("fail.nst"):
                raise RuntimeError("boom")
            return super().read_bytes(key)

    s3 = FlakyS3(payload=payload)
    usecase = ProcessNistUseCase(s3=s3, repository=repository, parser=parser, checksum=checksum)

    processed = usecase.execute()

    assert processed == 1
    assert any(level == "ERROR" and "fail.nst" in message for level, message in repository.log_calls)
    assert any(level == "INFO" and "ok.nst" in message for level, message in repository.log_calls)


def test_execute_handles_immutable_origin_base() -> None:
    payload = b"1:008 TSE\n"
    s3 = DummyS3(payload=payload)
    checksum = DummyChecksum()
    repository = DummyRepository(upsert_calls=[], log_calls=[])

    class ImmutableOriginBase:
        __slots__ = ("origin",)

        def __init__(self, origin: str) -> None:
            object.__setattr__(self, "origin", origin)

        def __setattr__(self, name: str, value) -> None:  # noqa: ANN001
            raise AttributeError("locked")

    class ImmutableParser(DummyParser):
        def parse(self, raw: bytes) -> tuple[Person, OriginBase]:
            return Person(), ImmutableOriginBase(origin="TSE")

    parser = ImmutableParser()
    usecase = ProcessNistUseCase(s3=s3, repository=repository, parser=parser, checksum=checksum)

    processed = usecase.execute()

    assert processed == 1
    assert any("Processed" in message for _, message in repository.log_calls)
