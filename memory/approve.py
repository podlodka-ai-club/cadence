"""Say what to write into the schema instead, on a draft schema change.

    python -m memory.approve NAME FILE [--db NAME]

- `NAME` — the draft in `schema_changes`, as `memory.propose` named it.
- `FILE` — the change: the text that replaces the sentence the finding blamed,
  worded for the schema as it will be given to the next memory.

A finding says what in the schema causes a fault; the change says what to put
there instead, and until it is written the draft is a question nobody has
answered. Writing it is a decision, and it is taken by whoever runs the loop —
a person, or a session carrying out a demonstration of it. The draft stays a
draft: `memory.gate --schema` decides it, once a memory has been written under
the changed schema and its cards observed.

Nothing here costs xmemory anything.
"""
import argparse
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import schema_changes
from storage.mongo import database


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", metavar="NAME", help="the draft schema change")
    parser.add_argument("path", metavar="FILE", help="the text to write into the schema instead")
    parser.add_argument("--db", default=None, help="database to work in (default: MONGO_DB)")
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as fh:
            change = fh.read().strip()
    except OSError as error:
        sys.exit(str(error))
    if not change:
        sys.exit("%s is empty: a change has to say what to write" % args.path)

    try:
        with database(args.db) as db:
            try:
                draft = schema_changes.named(db, [args.name])[0]
            except KeyError as error:
                sys.exit(error.args[0])
            if draft["status"] != "draft":
                sys.exit("schema change %s is %s already, not a draft" % (args.name, draft["status"]))
            schema_changes.approve(db, args.name, change)
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)

    where = ".".join(part for part in (draft.get("object"), draft.get("field")) if part)
    print("%s: change written%s\n\n%s" % (args.name, " for %s" % where if where else "", change))


if __name__ == "__main__":
    main()
