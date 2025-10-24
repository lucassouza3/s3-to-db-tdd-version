from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from minio.error import S3Error
from urllib3.response import HTTPResponse

from project.infra.s3.s3_manager import MinioS3Adapter, _field_1_008, _tag_matches


def test_campo_1_008_extracts_value() -> None:
    raw = b"1:008 TSE\r\n1:009 123"
    assert _field_1_008(raw) == "TSE"


def test_campo_1_008_handles_alternate_formats() -> None:
    assert _field_1_008(b"1.08:TSE") == "TSE"
    assert _field_1_008(b"1.0008=TSE") == "TSE"
    assert _field_1_008(b" \n1:008 TSE") == "TSE"


def test_campo_1_008_returns_none_when_missing() -> None:
    assert _field_1_008(b"no marker here") is None
    assert _field_1_008(b"") is None


def test_tag_matches_handles_edge_cases() -> None:
    assert _tag_matches("sem-digitos", 1, 8) is False
    assert _tag_matches("2:008", 1, 8) is False
    assert _tag_matches("1:008", 1, 8) is True


@dataclass
class DummyObject:
    object_name: str


class DummyResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class DummyClient:
    def __init__(self) -> None:
        self.objects: list[DummyObject] = []
        self.copies: list[tuple[str, str]] = []
        self.removed: list[str] = []
        self.uploads: list[tuple[str, bytes]] = []
        self.stat_calls: list[str] = []
        self.list_calls: list[tuple[str, bool]] = []
        self._stat_should_raise = False
        self._response_payload = b""
        self.last_response: DummyResponse | None = None

    def list_objects(self, bucket: str, prefix: str, recursive: bool) -> Iterable[DummyObject]:
        assert bucket == "bucket"
        self.list_calls.append((prefix, recursive))
        filtered = [obj for obj in self.objects if obj.object_name.startswith(prefix)]
        return list(filtered)

    def get_object(self, bucket: str, key: str) -> DummyResponse:
        assert bucket == "bucket"
        response = DummyResponse(self._response_payload)
        self.last_response = response
        return response

    def copy_object(self, bucket: str, dest_key: str, source) -> None:  # noqa: ANN001, D401
        assert bucket == "bucket"
        self.copies.append((dest_key, source.object_name))

    def remove_object(self, bucket: str, key: str) -> None:  # noqa: ANN001, D401
        assert bucket == "bucket"
        self.removed.append(key)

    def put_object(self, bucket: str, key: str, data: bytes, length: int) -> None:  # noqa: ANN001, D401
        assert bucket == "bucket"
        assert length == len(data)
        self.uploads.append((key, data))

    def stat_object(self, bucket: str, key: str):  # noqa: ANN001, D401
        assert bucket == "bucket"
        self.stat_calls.append(key)
        if self._stat_should_raise:
            raise S3Error(
                code="NoSuchKey",
                message="missing",
                resource=None,
                request_id=None,
                host_id=None,
                response=HTTPResponse(),
            )
        return {"key": key}


def test_list_nists_filters_extensions() -> None:
    client = DummyClient()
    client.objects = [
        DummyObject("nist/A/sample.nst"),
        DummyObject("nist/A/sample.txt"),
    ]
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    assert adapter.list_nists() == ["nist/A/sample.nst"]


def test_read_bytes_releases_response() -> None:
    client = DummyClient()
    client._response_payload = b"content"
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    data = adapter.read_bytes("nist/A/sample.nst")

    assert data == b"content"
    assert client.last_response is not None
    assert client.last_response.closed is True
    assert client.last_response.released is True


def test_move_processed_invokes_copy_and_delete() -> None:
    client = DummyClient()
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    adapter.move_processed("nist/A/sample.nst", "nist-lidos/A/sample.nst")

    assert client.copies == [("nist-lidos/A/sample.nst", "nist/A/sample.nst")]
    assert client.removed == ["nist/A/sample.nst"]


def test_upload_bytes_delegates_to_client() -> None:
    client = DummyClient()
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    adapter.upload_bytes("nist/A/sample.nst", b"abc")

    assert client.uploads == [("nist/A/sample.nst", b"abc")]


def test_object_exists_true() -> None:
    client = DummyClient()
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    assert adapter.object_exists("nist/A/sample.nst") is True
    assert client.stat_calls == ["nist/A/sample.nst"]


def test_object_exists_false_on_s3_error() -> None:
    client = DummyClient()
    client._stat_should_raise = True
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    assert adapter.object_exists("nist/A/sample.nst") is False


def test_delete_object_calls_client() -> None:
    client = DummyClient()
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    adapter.delete_object("nist/A/sample.nst")

    assert client.removed == ["nist/A/sample.nst"]


def test_delete_prefix_removes_matching_objects() -> None:
    client = DummyClient()
    client.objects = [
        DummyObject("nist/A/1.nst"),
        DummyObject("nist/B/2.nst"),
        DummyObject("other/ignore.nst"),
    ]
    adapter = MinioS3Adapter(client=client, bucket="bucket")

    removed = adapter.delete_prefix("nist/")

    assert removed == 2
    assert client.removed == ["nist/A/1.nst", "nist/B/2.nst"]

