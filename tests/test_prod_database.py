"""Production must use Postgres via DATABASE_URL. The original bug: prod.py
silently fell through to base.py's SQLite at db.sqlite3, which on Render's
ephemeral filesystem is wiped on every restart — every member's profile and
service rows were lost on the next deploy / sleep cycle.

These tests pin the contract so a future refactor can't ship a prod settings
file that quietly drops back to SQLite.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest


PROD_MODULE = "config.settings.prod"


def _load_prod_with_env(env):
    """Reload `config.settings.prod` under a controlled os.environ.

    Returns the reloaded module (or raises whatever the load raised).
    """
    saved_env = os.environ.copy()
    saved_module = sys.modules.pop(PROD_MODULE, None)
    saved_base = sys.modules.pop("config.settings.base", None)
    try:
        os.environ.clear()
        os.environ.update(env)
        return importlib.import_module(PROD_MODULE)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
        # Restore the previously cached modules so the next test sees a clean
        # state rather than the env-controlled load.
        sys.modules.pop(PROD_MODULE, None)
        if saved_module is not None:
            sys.modules[PROD_MODULE] = saved_module
        if saved_base is not None:
            sys.modules["config.settings.base"] = saved_base


def _good_env(**overrides):
    env = {
        "SECRET_KEY": "x" * 60,
        "PEPPER": "y" * 60,
        "DATABASE_URL": "postgres://user:pw@db.example/sjdb",
        "ALLOWED_HOSTS": "sadaqajariyah.online",
        "CSRF_TRUSTED_ORIGINS": "https://sadaqajariyah.online",
        "SITE_IS_PRODUCTION": "1",
    }
    env.update(overrides)
    return env


def test_prod_settings_load_with_postgres_url():
    """Sanity: with all required env vars set, prod settings load cleanly
    and route DATABASES at the Postgres URL."""
    mod = _load_prod_with_env(_good_env())
    assert mod.DEBUG is False
    db = mod.DATABASES["default"]
    assert "postgresql" in db["ENGINE"], (
        f"prod must use the Postgres engine; got {db['ENGINE']!r}"
    )
    assert db["NAME"] == "sjdb"
    assert db["HOST"] == "db.example"


def test_prod_fails_loud_without_database_url():
    """The original bug: a missing DATABASE_URL silently fell back to SQLite.
    Now it must raise on import."""
    env = _good_env()
    env.pop("DATABASE_URL")
    with pytest.raises(AssertionError, match="DATABASE_URL is required"):
        _load_prod_with_env(env)


def test_prod_rejects_sqlite_database_url():
    """A misconfigured DATABASE_URL pointing at SQLite must also fail loud —
    it would have the same data-loss outcome on Render."""
    env = _good_env(DATABASE_URL="sqlite:///tmp/foo.db")
    with pytest.raises(AssertionError, match="must point at Postgres"):
        _load_prod_with_env(env)


def test_prod_database_has_persistent_connection():
    """conn_max_age > 0 reuses the Postgres connection across requests, which
    matters for free-tier dyno performance. Pinning here so a future refactor
    doesn't drop it."""
    mod = _load_prod_with_env(_good_env())
    db = mod.DATABASES["default"]
    assert db.get("CONN_MAX_AGE", 0) >= 60, (
        f"prod DB should keep persistent connections; CONN_MAX_AGE={db.get('CONN_MAX_AGE')}"
    )


def test_prod_database_requires_ssl():
    """Render's managed Postgres requires TLS. Don't ship a config that connects
    in plaintext."""
    mod = _load_prod_with_env(_good_env())
    db = mod.DATABASES["default"]
    options = db.get("OPTIONS") or {}
    assert options.get("sslmode") in ("require", "verify-full", "verify-ca"), (
        f"prod Postgres connection must require TLS; sslmode={options.get('sslmode')!r}"
    )


def test_prod_module_imports_dj_database_url():
    """The library is the only path that turns DATABASE_URL into a Django
    DATABASES dict — confirm it's actually imported in prod.py."""
    text = Path(__file__).resolve().parent.parent.joinpath(
        "config", "settings", "prod.py"
    ).read_text()
    assert "import dj_database_url" in text or "from dj_database_url" in text


def test_dj_database_url_pinned_in_requirements():
    text = Path(__file__).resolve().parent.parent.joinpath("requirements.txt").read_text()
    assert "dj-database-url" in text or "dj_database_url" in text


def test_psycopg_pinned_in_requirements():
    """psycopg is the Postgres driver — without it, dj_database_url's
    ENGINE='django.db.backends.postgresql' fails to load at runtime."""
    text = Path(__file__).resolve().parent.parent.joinpath("requirements.txt").read_text()
    assert "psycopg" in text
