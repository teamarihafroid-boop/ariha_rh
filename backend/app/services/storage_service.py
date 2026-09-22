from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import get_settings

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class StorageServiceError(ValueError):
    pass


class StorageBackend(Protocol):
    def save(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalFilesystemStorage:
    """Dev-only backend. Never selected in production — see get_storage()."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)

    def _resolve(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        if self._base_dir.resolve() not in path.parents and path != self._base_dir.resolve():
            raise StorageServiceError("Clé de stockage invalide.")
        return path

    def save(self, key: str, content: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)


class S3Storage:
    """S3-compatible object storage (Cloudflare R2, AWS S3, ...) — the
    production backend. Files are never exposed as direct storage URLs;
    every read still goes through an authenticated FastAPI route (see
    routers/employees.py, routers/recruitment.py), which calls .read() and
    streams the bytes back itself. See TECHNICAL_DECISIONS.md §7."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None,
        access_key_id: str,
        secret_access_key: str,
        region: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            # R2 (and some other S3-compatible providers) need path-style
            # addressing rather than the AWS-default virtual-hosted style.
            config=BotoConfig(s3={"addressing_style": "path"}),
        )

    def save(self, key: str, content: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)

    def read(self, key: str) -> bytes:
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise StorageServiceError(f"Fichier introuvable : {key}") from exc
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def build_key(entity: str, entity_id: int, original_filename: str) -> str:
    """Server-generated key — never derived from the client-supplied filename,
    so a crafted filename can't traverse outside the entity's own folder."""
    ext = Path(original_filename).suffix[:10]  # keep it short, still useful for downloads
    return f"{entity}/{entity_id}/{uuid.uuid4().hex}{ext}"


@lru_cache
def _s3_storage() -> S3Storage:
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("STORAGE_S3_BUCKET", settings.storage_s3_bucket),
            ("STORAGE_S3_ACCESS_KEY_ID", settings.storage_s3_access_key_id),
            ("STORAGE_S3_SECRET_ACCESS_KEY", settings.storage_s3_secret_access_key),
        )
        if not value
    ]
    if missing:
        raise StorageServiceError(
            f"STORAGE_BACKEND=s3 requires {', '.join(missing)} to be set. "
            "See .env.example and TECHNICAL_DECISIONS.md §7."
        )
    return S3Storage(
        bucket=settings.storage_s3_bucket,  # type: ignore[arg-type]
        endpoint_url=settings.storage_s3_endpoint_url,
        access_key_id=settings.storage_s3_access_key_id,  # type: ignore[arg-type]
        secret_access_key=settings.storage_s3_secret_access_key,  # type: ignore[arg-type]
        region=settings.storage_s3_region,
    )


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "local":
        if settings.env == "production":
            raise StorageServiceError(
                "STORAGE_BACKEND=local is refused when ENV=production — Railway's filesystem "
                "isn't reliably persistent across redeploys. Configure an S3-compatible backend "
                "(e.g. Cloudflare R2) instead. See TECHNICAL_DECISIONS.md §7."
            )
        return LocalFilesystemStorage(get_settings().storage_local_dir)
    if settings.storage_backend == "s3":
        return _s3_storage()
    raise StorageServiceError(f"Backend de stockage inconnu : {settings.storage_backend!r}")
