from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.services import storage_service


def test_local_filesystem_storage_round_trip(tmp_path):
    storage = storage_service.LocalFilesystemStorage(str(tmp_path))
    key = storage_service.build_key("employees", 1, "contrat.pdf")

    storage.save(key, b"hello world")
    assert storage.read(key) == b"hello world"

    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)


def test_build_key_is_server_generated_not_from_client_filename():
    key_a = storage_service.build_key("candidates", 3, "../../etc/passwd")
    key_b = storage_service.build_key("candidates", 3, "cv.pdf")
    assert key_a.startswith("candidates/3/")
    assert ".." not in key_a
    assert key_a != key_b


def test_get_storage_refuses_local_backend_in_production(monkeypatch):
    # get_settings() is lru_cache'd — mutating the already-cached singleton in
    # place (rather than clearing the cache) means every get_settings() call
    # anywhere, including inside get_storage(), sees the same patched values.
    settings = storage_service.get_settings()
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "storage_backend", "local")

    with pytest.raises(storage_service.StorageServiceError):
        storage_service.get_storage()


def test_get_storage_returns_local_backend_outside_production(monkeypatch):
    settings = storage_service.get_settings()
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "storage_backend", "local")

    backend = storage_service.get_storage()
    assert isinstance(backend, storage_service.LocalFilesystemStorage)


# ------------------------------------------------------------------ S3 --


@pytest.fixture(autouse=True)
def _clear_s3_storage_cache():
    # _s3_storage() is lru_cache'd (a real boto3 client shouldn't be rebuilt
    # on every request) — clear it before and after each test so one test's
    # monkeypatched settings/mocked boto3.client can't leak into another.
    storage_service._s3_storage.cache_clear()
    yield
    storage_service._s3_storage.cache_clear()


def test_get_storage_s3_requires_bucket_and_credentials(monkeypatch):
    settings = storage_service.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_s3_bucket", None)
    monkeypatch.setattr(settings, "storage_s3_access_key_id", None)
    monkeypatch.setattr(settings, "storage_s3_secret_access_key", None)

    with pytest.raises(storage_service.StorageServiceError, match="STORAGE_S3_BUCKET"):
        storage_service.get_storage()


def test_get_storage_returns_s3_backend_when_fully_configured(monkeypatch):
    settings = storage_service.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_s3_bucket", "ariha-documents")
    monkeypatch.setattr(
        settings, "storage_s3_endpoint_url", "https://example.r2.cloudflarestorage.com"
    )
    monkeypatch.setattr(settings, "storage_s3_access_key_id", "test-key-id")
    monkeypatch.setattr(settings, "storage_s3_secret_access_key", "test-secret")
    monkeypatch.setattr(storage_service.boto3, "client", MagicMock())

    backend = storage_service.get_storage()
    assert isinstance(backend, storage_service.S3Storage)


def test_s3_storage_save_read_delete_use_the_right_bucket_and_key():
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": MagicMock(read=lambda: b"file bytes")}

    backend = storage_service.S3Storage.__new__(storage_service.S3Storage)
    backend._bucket = "ariha-documents"
    backend._client = mock_client

    backend.save("employees/1/abc.pdf", b"content")
    mock_client.put_object.assert_called_once_with(
        Bucket="ariha-documents", Key="employees/1/abc.pdf", Body=b"content"
    )

    assert backend.read("employees/1/abc.pdf") == b"file bytes"
    mock_client.get_object.assert_called_once_with(
        Bucket="ariha-documents", Key="employees/1/abc.pdf"
    )

    backend.delete("employees/1/abc.pdf")
    mock_client.delete_object.assert_called_once_with(
        Bucket="ariha-documents", Key="employees/1/abc.pdf"
    )


def test_s3_storage_read_wraps_missing_object_error():
    mock_client = MagicMock()
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "not found"}}, "GetObject"
    )

    backend = storage_service.S3Storage.__new__(storage_service.S3Storage)
    backend._bucket = "ariha-documents"
    backend._client = mock_client

    with pytest.raises(storage_service.StorageServiceError):
        backend.read("employees/1/missing.pdf")
