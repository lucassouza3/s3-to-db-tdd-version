from __future__ import annotations

from project.application.services.checksum_service import ChecksumService


def test_md5_bytes_matches_known_values() -> None:
    checksum = ChecksumService()

    assert checksum.md5_bytes(b"") == "d41d8cd98f00b204e9800998ecf8427e"
    assert checksum.md5_bytes(b"abc") == "900150983cd24fb0d6963f7d28e17f72"
