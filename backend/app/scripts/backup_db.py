"""Nightly database backup: pg_dump -> gzip -> upload to the same object
storage as file uploads (see TECHNICAL_DECISIONS.md §8's "Backups" note —
Railway's managed Postgres backups are the first line, this is the
independent second one, so a Railway-only outage can't take both out).

Run as a one-off command against the same image as the main app (it's
installed on the same PATH, see Dockerfile's postgresql-client layer):

    python -m app.scripts.backup_db

Intended to run on a schedule via Railway's Cron Jobs (a service sharing
this image, with this as its start command) — see docs/DEPLOYMENT.md.
"""

from __future__ import annotations

import gzip
import subprocess
import sys
from datetime import UTC, datetime

from app.config import get_settings
from app.services import storage_service


def run() -> None:
    settings = get_settings()
    if settings.storage_backend != "s3":
        print(
            "STORAGE_BACKEND != s3 — refusing to run in an environment with no durable "
            "off-Railway destination for the dump.",
            file=sys.stderr,
        )
        sys.exit(1)

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    key = f"backups/postgres/{timestamp}.sql.gz"

    print("Dumping database via pg_dump...")
    dump = subprocess.run(
        ["pg_dump", "--no-owner", "--no-privileges", settings.database_url.replace("+psycopg", "")],
        capture_output=True,
        check=True,
    )
    compressed = gzip.compress(dump.stdout)
    print(f"Dump complete: {len(compressed) / 1024:.1f} KB compressed. Uploading to {key}...")

    storage_service.get_storage().save(key, compressed)
    print("Backup uploaded successfully.")


if __name__ == "__main__":
    run()
