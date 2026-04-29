"""Verifies alembic upgrade/downgrade is reversible.

Requires Postgres + pgvector running. Run with:
    docker compose up -d postgres-pgvector
"""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

import pytest


def _db_available() -> bool:
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5432"))
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres not running. Start with: docker compose up -d postgres-pgvector",
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["alembic", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class TestMigrationRoundtrip:
    def test_upgrade_downgrade_upgrade(self) -> None:
        # Reset to base
        down = _alembic("downgrade", "base")
        # If no tables yet, this is fine — alembic returns 0 even when nothing to do
        assert down.returncode == 0, f"downgrade failed: {down.stderr}"

        up1 = _alembic("upgrade", "head")
        assert up1.returncode == 0, f"first upgrade failed: {up1.stderr}"

        down2 = _alembic("downgrade", "base")
        assert down2.returncode == 0, f"second downgrade failed: {down2.stderr}"

        up2 = _alembic("upgrade", "head")
        assert up2.returncode == 0, f"second upgrade failed: {up2.stderr}"
