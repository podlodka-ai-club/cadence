"""Credentials, and the connection they open.

Two settings, read from the repository's `.env` — see `envfile`:

    MONGO_URI   the whole connection string, user and password included
    MONGO_DB    which database to work in
"""
from contextlib import contextmanager

from pymongo import MongoClient

import envfile

DEFAULT_DB = "cadence_eval"


def settings():
    """The connection string and the database name, environment over file."""
    values = envfile.by_prefix("MONGO_")
    uri = envfile.require(values, "MONGO_URI",
                          "copy .env.example to .env and fill it in, or export it")
    return uri, values.get("MONGO_DB") or DEFAULT_DB


@contextmanager
def database(name=None):
    """A handle on the database, closed when the block ends."""
    uri, configured = settings()
    # tz_aware: Mongo keeps dates in UTC, and a card refuses a date without a
    # zone, so a date read back has to come out aware as it went in.
    client = MongoClient(uri, serverSelectionTimeoutMS=10000, tz_aware=True)
    try:
        yield client[name or configured]
    finally:
        client.close()
