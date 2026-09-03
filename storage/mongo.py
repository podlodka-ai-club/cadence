"""Credentials, and the connection they open.

Credentials live in `.env` at the repository root, which git ignores — a
connection string carries a password, so it never enters the tree. Copy
`.env.example` to `.env` and fill it in.

Two settings:

    MONGO_URI   the whole connection string, user and password included
    MONGO_DB    which database to work in

Both can also come from the real environment, which wins over the file: a
one-off run against another database needs no edit, only

    MONGO_DB=cadence_test python -m storage.setup
"""
import os
from contextlib import contextmanager

from pymongo import MongoClient

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(REPO, ".env")
DEFAULT_DB = "cadence_eval"


def read_env_file(path=ENV_FILE):
    """`KEY=value` lines from an env file. Blank lines and `#` comments are skipped."""
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep:
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def settings(path=ENV_FILE):
    """The connection string and the database name, environment over file."""
    values = read_env_file(path)
    values.update((key, value) for key, value in os.environ.items() if key.startswith("MONGO_"))
    uri = values.get("MONGO_URI")
    if not uri:
        raise SystemExit(
            "no MONGO_URI: copy .env.example to .env and fill it in, or export it")
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
