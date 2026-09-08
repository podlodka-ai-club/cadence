"""Record the answers about cards from a JSON file.

    python -m storage.load_answers FILE [--db NAME] [--dry-run]

- `FILE` — a list of answers: `[{"source": …, "externalId": …, "accept": true},
  {"source": …, "externalId": …, "accept": false, "reasons": ["missing_time"]}, …]`.
  Reasons belong to a refusal only, and come from the closed list `storage`
  describes.
- `--db NAME` — database to write into (default: MONGO_DB).
- `--dry-run` — read and report, without writing anything.

There is one answer per card: an answer already given about a card is replaced
by the one in the file. An answer about a card the database does not hold is
refused before anything is written. Load the cards first.
"""
import argparse
import json
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import answers
from storage.mongo import database
from storage.schema import REASONS


def read(path):
    """The answers as the file gives them: `(source, externalId, accept, reasons)`."""
    with open(path, encoding="utf-8") as fh:
        entries = json.load(fh)
    if not isinstance(entries, list):
        raise ValueError("%s is not a list of answers" % path)
    found = []
    for entry in entries:
        try:
            source, external_id, accept = entry["source"], str(entry["externalId"]), bool(entry["accept"])
        except (KeyError, TypeError):
            raise ValueError("%s: an answer without a source, externalId or accept: %r" % (path, entry))
        reasons = list(entry.get("reasons", []))
        unknown = [reason for reason in reasons if reason not in REASONS]
        if unknown:
            raise ValueError("%s: %s/%s refused for a reason not on the list: %s"
                             % (path, source, external_id, ", ".join(unknown)))
        found.append((source, external_id, accept, reasons))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", metavar="FILE", help="the answers, as JSON")
    parser.add_argument("--db", default=None, help="database to write into (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the file and report, without writing anything")
    args = parser.parse_args(argv)

    try:
        found = read(args.path)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    accepted = sum(1 for _, _, accept, _ in found if accept)
    print("%d answers: %d accepted, %d refused" % (len(found), accepted, len(found) - accepted))
    if args.dry_run:
        print("nothing written")
        return

    try:
        with database(args.db) as db:
            missing = [(source, external_id) for source, external_id, _, _ in found
                       if db.cards.find_one({"source": source, "externalId": external_id}, {"_id": 1}) is None]
            if missing:
                sys.exit("%d of the cards are not in %s.cards, e.g. %s/%s — load the cards first"
                         % (len(missing), db.name, missing[0][0], missing[0][1]))
            for source, external_id, accept, reasons in found:
                answers.record(db, source, external_id, accept, reasons)
            print("%d answers written to %s.answers" % (len(found), db.name))
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)


if __name__ == "__main__":
    main()
