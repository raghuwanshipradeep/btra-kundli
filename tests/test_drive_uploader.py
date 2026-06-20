from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

import drive_uploader
from config import settings


SAMPLE_PDF = b"%PDF-1.4 minimal test bytes"


def _make_service(next_chunk_side_effect):
    """Build a fake Drive service whose upload request.next_chunk() is driven
    by `next_chunk_side_effect` (an exception to raise every call, or a list of
    (status, response) tuples returned in order)."""
    service = MagicMock()
    request = MagicMock()
    request.next_chunk.side_effect = next_chunk_side_effect
    service.files.return_value.create.return_value = request
    return service, request


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    # Don't actually wait through the exponential backoff during tests.
    monkeypatch.setattr(drive_uploader.time, "sleep", lambda _s: None)


def test_timeout_error_triggers_retries(monkeypatch):
    """The production bug: a write TimeoutError must now flow through the retry
    loop (3 attempts) instead of failing on the first try."""
    service, request = _make_service(TimeoutError("The write operation timed out"))
    monkeypatch.setattr(drive_uploader, "_get_drive_service", lambda: service)

    with pytest.raises(TimeoutError):
        drive_uploader._upload_sync(SAMPLE_PDF, "f.pdf", "folder123", "desc")

    assert request.next_chunk.call_count == 3


def test_http_error_5xx_triggers_retries(monkeypatch):
    """Transient 5xx from Drive should be retried too."""
    resp = MagicMock(status=503, reason="Service Unavailable")
    err = HttpError(resp, b"unavailable")
    service, request = _make_service(err)
    monkeypatch.setattr(drive_uploader, "_get_drive_service", lambda: service)

    with pytest.raises(HttpError):
        drive_uploader._upload_sync(SAMPLE_PDF, "f.pdf", "folder123", "desc")

    assert request.next_chunk.call_count == 3


def test_successful_upload_returns_response_in_one_attempt(monkeypatch):
    """A clean upload still uploads exactly once and returns the API response."""
    response = {"id": "file_abc", "name": "f.pdf", "webViewLink": "https://x"}
    service, request = _make_service([(None, response)])
    monkeypatch.setattr(drive_uploader, "_get_drive_service", lambda: service)

    result = drive_uploader._upload_sync(SAMPLE_PDF, "f.pdf", "folder123", "desc")

    assert result == response
    assert request.next_chunk.call_count == 1


def test_recovers_after_transient_then_succeeds(monkeypatch):
    """First attempt times out, second succeeds — result is returned, no raise."""
    response = {"id": "file_xyz", "name": "f.pdf"}
    service = MagicMock()
    attempt1 = MagicMock()
    attempt1.next_chunk.side_effect = TimeoutError("timeout")
    attempt2 = MagicMock()
    attempt2.next_chunk.side_effect = [(None, response)]
    service.files.return_value.create.side_effect = [attempt1, attempt2]
    monkeypatch.setattr(drive_uploader, "_get_drive_service", lambda: service)

    result = drive_uploader._upload_sync(SAMPLE_PDF, "f.pdf", "folder123", "desc")

    assert result == response


def test_timeout_setting_default():
    """The explicit Drive socket timeout setting exists with a sane default."""
    assert settings.drive_upload_timeout_seconds >= 60
