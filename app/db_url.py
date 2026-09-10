"""Derive driver-specific connection URLs from a single Neon connection string.

Neon gives you a standard libpq URL (postgresql://...?sslmode=require&
channel_binding=require). psycopg2 (used by Alembic for sync migrations)
understands that as-is. asyncpg (used by the app at runtime) does not
understand `channel_binding` at all, and wants SSL configured via
connect_args rather than a `sslmode` query param. Neon's pooled endpoint
(the "-pooler" host, PgBouncer in transaction mode) also requires disabling
asyncpg's prepared-statement cache, or queries intermittently fail with
"prepared statement already exists".
"""

from sqlalchemy.engine import URL, make_url


def build_async_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    query = {k: v for k, v in url.query.items() if k not in ("sslmode", "channel_binding")}
    return url.set(drivername="postgresql+asyncpg", query=query)


def async_connect_args(raw_url: str) -> dict:
    url = make_url(raw_url)
    connect_args: dict = {"statement_cache_size": 0}
    if url.query.get("sslmode") or (url.host and "neon.tech" in url.host):
        connect_args["ssl"] = "require"
    return connect_args


def build_sync_url(raw_url: str) -> URL:
    # channel_binding=require trips up some psycopg2/libpq builds during SCRAM
    # auth (surfaces as a misleading "password authentication failed"); the
    # connection is already encrypted via sslmode=require, so drop it here.
    url = make_url(raw_url)
    query = {k: v for k, v in url.query.items() if k != "channel_binding"}
    return url.set(drivername="postgresql+psycopg2", query=query)
