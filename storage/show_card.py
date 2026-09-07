"""Print one card as JSON, by the pair that addresses it.

    python -m storage.show_card SOURCE EXTERNAL_ID [--db NAME]

For whoever needs the post behind a record and has only its identity: the
text as it stood in the source, its posting date and its links. Reads and
prints, and touches nothing.
"""
import argparse
import json

from pymongo.errors import PyMongoError

from storage.mongo import database


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="the source the post came from, e.g. t.me/a_channel")
    parser.add_argument("external_id", metavar="EXTERNAL_ID", help="the post's number in that source")
    parser.add_argument("--db", default=None, help="database to read from (default: MONGO_DB)")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            card = db.cards.find_one(
                {"source": args.source, "externalId": args.external_id}, {"_id": 0})
    except PyMongoError as error:
        raise SystemExit("database error: %s" % error)
    if card is None:
        raise SystemExit("no card %s/%s" % (args.source, args.external_id))
    card["date"] = card["date"].isoformat()
    print(json.dumps(card, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
