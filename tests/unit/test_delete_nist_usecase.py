from __future__ import annotations

from dataclasses import dataclass

from project.application.usecases.delete_nist_usecase import DeleteNistUseCase


@dataclass
class DummyS3:
    removed_keys: list[str]
    removed_prefixes: list[str]

    def delete_object(self, key: str) -> None:
        self.removed_keys.append(key)

    def delete_prefix(self, prefix: str) -> int:
        self.removed_prefixes.append(prefix)
        return 2


def test_delete_by_key_calls_port() -> None:
    dummy = DummyS3(removed_keys=[], removed_prefixes=[])
    usecase = DeleteNistUseCase(s3=dummy)

    usecase.delete_by_key("nist/A/sample.nst")

    assert dummy.removed_keys == ["nist/A/sample.nst"]


def test_delete_by_prefix_returns_count() -> None:
    dummy = DummyS3(removed_keys=[], removed_prefixes=[])
    usecase = DeleteNistUseCase(s3=dummy)

    removed = usecase.delete_by_prefix("nist/")

    assert removed == 2
    assert dummy.removed_prefixes == ["nist/"]


def test_delete_all_uses_empty_prefix() -> None:
    dummy = DummyS3(removed_keys=[], removed_prefixes=[])
    usecase = DeleteNistUseCase(s3=dummy)

    removed = usecase.delete_all()

    assert removed == 2
    assert dummy.removed_prefixes == [""]
