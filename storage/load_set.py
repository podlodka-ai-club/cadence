"""Write a named set of cards from a JSON file.

    python -m storage.load_set FILE [--db NAME] [--dry-run]

- `FILE` — the set: `{"name": …, "note": …, "cards": [{"source": …,
  "externalId": …, "why": [...]}, …]}`. The cards go in the order the file
  lists them, and that order is part of the set.
- `--db NAME` — database to write into (default: MONGO_DB).
- `--dry-run` — read and report, without writing anything.

A set is written once and not edited: a name already taken is refused, and a
set naming a card the database does not hold is refused before anything is
written. Load the cards first.
"""
import argparse
import json
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import sets
from storage.mongo import database


def read(path):
    """The set as the file gives it: name, note, and `(source, externalId, why)` triples."""
    with open(path, encoding="utf-8") as fh:
        document = json.load(fh)
    if not isinstance(document, dict) or not document.get("name") or not document.get("cards"):
        raise ValueError("%s is not a set: it needs a name and cards" % path)
    cards = []
    for entry in document["cards"]:
        try:
            cards.append((entry["source"], str(entry["externalId"]), list(entry.get("why", []))))
        except (KeyError, TypeError):
            raise ValueError("%s: a card without a source or externalId: %r" % (path, entry))
    return document["name"], document.get("note"), cards


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", metavar="FILE", help="the set, as JSON")
    parser.add_argument("--db", default=None, help="database to write into (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the file and report, without writing anything")
    args = parser.parse_args(argv)

    try:
        name, note, cards = read(args.path)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    print("%s: %d cards" % (name, len(cards)))
    if args.dry_run:
        print("nothing written")
        return

    try:
        with database(args.db) as db:
            missing = [(source, external_id) for source, external_id, _ in cards
                       if db.cards.find_one({"source": source, "externalId": external_id}, {"_id": 1}) is None]
            if missing:
                sys.exit("%d of the cards are not in %s.cards, e.g. %s/%s — load the cards first"
                         % (len(missing), db.name, missing[0][0], missing[0][1]))
            try:
                sets.define(db, name, cards, note=note)
            except ValueError as error:
                sys.exit(str(error))
            print("set %s written to %s.sets" % (name, db.name))
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)


if __name__ == "__main__":
    main()
