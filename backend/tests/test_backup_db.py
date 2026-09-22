from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.scripts import backup_db


def test_backup_refuses_when_not_s3_backend(monkeypatch):
    settings = backup_db.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "local")

    with pytest.raises(SystemExit):
        backup_db.run()


def test_backup_dumps_and_uploads_when_s3_backend(monkeypatch):
    settings = backup_db.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")

    fake_dump = MagicMock(stdout=b"-- sql dump --")
    fake_storage = MagicMock()

    with (
        patch("app.scripts.backup_db.subprocess.run", return_value=fake_dump) as run_mock,
        patch("app.scripts.backup_db.storage_service.get_storage", return_value=fake_storage),
    ):
        backup_db.run()

    run_mock.assert_called_once()
    assert run_mock.call_args.args[0][0] == "pg_dump"
    fake_storage.save.assert_called_once()
    key = fake_storage.save.call_args.args[0]
    assert key.startswith("backups/postgres/")
    assert key.endswith(".sql.gz")
