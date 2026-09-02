"""Put cards that exist as JSON files into the `cards` collection.

    python -m storage.load_cards [PATH ...] [--db NAME] [--dry-run]

- `PATH` — a card file, or a directory searched for `.json` files at any
  depth. Defaults to the cards of the working material.
- `--db NAME` — database to load into (default: MONGO_DB).
- `--dry-run` — read and report, without writing anything.

A card is addressed by `(source, externalId)` and written with an upsert, so
loading the same files twice leaves one copy of each. Loading again refreshes
the post itself — its text, its links, its date — and touches nothing else, so
an answer already given about a card survives it.

A file that is not a card stops the run before anything is written: a
half-loaded set is worse than none.
"""
import argparse
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import card_files
from storage.cards import upsert
from storage.mongo import database

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(REPO, "untracked", "cards")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", default=[DEFAULT_PATH],
                        help="a card file, or a directory of them (default: untracked/cards of the repository)")
    parser.add_argument("--db", default=None, help="database to load into (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the files and report, without writing anything")
    args = parser.parse_args(argv)

    paths = args.paths or [DEFAULT_PATH]
    for path in paths:
        if not os.path.exists(path):
            sys.exit("no such path: " + path)

    try:
        cards = card_files.read(paths)
    except ValueError as error:
        sys.exit(str(error))
    sources = sorted({card.source for card in cards})
    for source in sources:
        print("%-28s %5d cards" % (source, sum(1 for card in cards if card.source == source)))

    if args.dry_run:
        print("%d cards read, nothing written" % len(cards))
        return

    try:
        with database(args.db) as db:
            added, refreshed = upsert(db, cards)
            print("%d cards into %s.cards — %d new, %d refreshed" % (
                len(cards), db.name, added, refreshed))
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)


if __name__ == "__main__":
    main()
