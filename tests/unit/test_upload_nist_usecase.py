from __future__ import annotations

from pathlib import Path

from project.application.usecases.upload_nist_usecase import UploadNistUseCase


class DummyS3:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes]] = []

    def upload_bytes(self, key: str, raw: bytes) -> None:
        self.calls.append((key, raw))


class DummyParser:
    def compose_key_for_upload(self, filename: str, raw: bytes) -> str:  # noqa: ARG002
        return f"nist/TSE/{filename}"


def test_execute_reads_file_and_uploads(tmp_path: Path) -> None:
    target = tmp_path / "sample.nst"
    payload = b"example-nist-bytes"
    target.write_bytes(payload)

    s3 = DummyS3()
    parser = DummyParser()

    usecase = UploadNistUseCase(s3=s3, nist_tools=parser)

    key = usecase.execute(str(target))

    assert key == "nist/TSE/sample.nst"
    assert s3.calls == [("nist/TSE/sample.nst", payload)]
