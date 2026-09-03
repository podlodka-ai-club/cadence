"""Bring a database to the shape `storage.schema` describes.

Creates the collections that are missing, puts the current validator on the
ones that are already there, and creates the indexes. Idempotent: running it
twice changes nothing the second time, so it is the way to apply a change to
the schema as well as the way to start an empty database.

    python -m storage.setup [COLLECTION ...] [--db NAME]

`COLLECTION` names what to bring up, and defaults to everything in the schema.
Not every database holds every collection — the evaluation set keeps answers
that production has no use for, production reads sources that the evaluation
set never polls — so a database is told which of them are its own.

`--db` defaults to MONGO_DB from `.env`.
"""
import argparse

from pymongo.errors import PyMongoError

from storage.mongo import database
from storage.schema import COLLECTIONS


def ensure(db, name, definition):
    """Create or update one collection. Returns what it did, for the report."""
    validation = {
        "validator": definition["validator"],
        "validationLevel": "strict",
        "validationAction": "error",
    }
    if name in db.list_collection_names():
        db.command("collMod", name, **validation)
        done = "validator updated"
    else:
        db.create_collection(name, **validation)
        done = "created"
    for index in definition["indexes"]:
        db[name].create_index(index["keys"], name=index["name"], unique=index["unique"] if "unique" in index else False)
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("collections", nargs="*", metavar="COLLECTION",
                        help="collections to bring up (default: all of them — %s)" % ", ".join(COLLECTIONS))
    parser.add_argument("--db", default=None, help="database to set up (default: MONGO_DB)")
    args = parser.parse_args(argv)

    unknown = [name for name in args.collections if name not in COLLECTIONS]
    if unknown:
        raise SystemExit("no such collection: %s — the schema has %s" % (
            ", ".join(unknown), ", ".join(COLLECTIONS)))
    wanted = args.collections or list(COLLECTIONS)

    try:
        with database(args.db) as db:
            for name in wanted:
                definition = COLLECTIONS[name]
                done = ensure(db, name, definition)
                print("%-10s %-18s %d indexes" % (name, done, len(definition["indexes"])))
            print("%s is ready" % db.name)
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)


if __name__ == "__main__":
    main()
