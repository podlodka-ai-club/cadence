"""The repository's `.env` — the one place a credential is read from.

A connection string carries a password and an API key is a key, so neither
belongs in the tree: both live in `.env` at the repository root, which git
ignores. Copy `.env.example` to `.env` and fill it in.

Every setting can also come from the real environment, which wins over the
file — a one-off run against another database needs no edit, only

    MONGO_DB=cadence_test python -m storage.setup

Settings are read by prefix, so each part of the repository asks for its own
and sees nothing else:

    values = envfile.by_prefix("TELEGRAM_")
"""
import os

REPO = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(REPO, ".env")


def read(path=ENV_FILE):
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


def by_prefix(prefix, path=ENV_FILE):
    """Settings whose name starts with `prefix`, environment over file."""
    values = {key: value for key, value in read(path).items() if key.startswith(prefix)}
    values.update((key, value) for key, value in os.environ.items() if key.startswith(prefix))
    return values


def require(values, key, hint):
    """One setting that has to be there, or an exit saying how to supply it."""
    value = values.get(key)
    if not value:
        raise SystemExit("no %s: %s" % (key, hint))
    return value
