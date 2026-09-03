"""Add a source for the online parser to read.

    python -m storage.add_source SOURCE [--db NAME] [--since WHEN]

- `SOURCE` — the name the cards will carry, `t.me/a_channel`.
- `--db NAME` — database to add it to (default: MONGO_DB).
- `--since WHEN` — read posts from this moment on, as `2026-08-15` or
  `2026-08-15T09:00:00+03:00`. A moment given without a zone is read as UTC.

Reading starts where the cards already stored for the source end: history comes
from an export, and the parser picks up from the last post it left. A source
with no cards is read from now on, so adding a channel never pulls its archive.

Adding the same source twice changes nothing — the second run reports what is
already there and leaves the cursor alone.
"""
import argparse
import os
import sys
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.card import SOURCE_NAME
from storage import sources
from storage.cards import newest_date
from storage.mongo import database


def moment(text):
    """A moment from the command line. Without a zone it is read as UTC."""
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "not a date or a time: %r — try 2026-08-15 or 2026-08-15T09:00:00+03:00" % text)
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def start_of(db, source, since=None):
    """When to start reading a source, and why — for the report."""
    if since is not None:
        return since, "as asked"
    newest = newest_date(db, source)
    if newest is not None:
        return newest, "where the cards already stored end"
    return sources.now(), "now — the source has no cards to continue from"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", metavar="SOURCE", help="the source name, `t.me/a_channel`")
    parser.add_argument("--db", default=None, help="database to add it to (default: MONGO_DB)")
    parser.add_argument("--since", type=moment, default=None,
                        help="read posts from this moment on")
    args = parser.parse_args(argv)

    if not SOURCE_NAME.match(args.source):
        sys.exit("not a usable source name: %r" % args.source)

    try:
        with database(args.db) as db:
            existing = db.sources.find_one({"source": args.source})
            if existing is not None:
                print("%s is already a source of %s, reading from %s" % (
                    args.source, db.name, existing["startAt"].isoformat()))
                return
            start_at, why = start_of(db, args.source, args.since)
            sources.add(db, args.source, start_at)
            print("%s added to %s, reading from %s — %s" % (
                args.source, db.name, start_at.isoformat(), why))
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)


if __name__ == "__main__":
    main()
