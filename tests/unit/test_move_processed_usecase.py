from __future__ import annotations

from project.application.usecases.move_processed_usecase import MoveProcessedUseCase


class DummyS3:
    def __init__(self) -> None:
        self.moves: list[tuple[str, str]] = []

    def move_processed(self, key: str, dest: str) -> None:
        self.moves.append((key, dest))


class DummyParser:
    def destination_key_for_processed(self, key: str, raw: bytes) -> str:  # noqa: ARG002
        return f"nist-lidos/TSE/{key.split('/')[-1]}"


def test_execute_moves_object_and_returns_destination() -> None:
    s3 = DummyS3()
    parser = DummyParser()
    usecase = MoveProcessedUseCase(s3=s3, nist_tools=parser)

    dest = usecase.execute("nist/TSE/116908146.nst", b"...")

    assert dest == "nist-lidos/TSE/116908146.nst"
    assert s3.moves == [("nist/TSE/116908146.nst", "nist-lidos/TSE/116908146.nst")]
