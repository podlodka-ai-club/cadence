"""Answer cards by hand, through a page in the browser.

    python -m admin [--config PATH] [--db NAME]

Which cards a run works on comes from `admin/config.json`; see `admin.config`.
Where they are written comes from `.env`; see `storage.mongo`.
"""
import argparse
import sys

from pymongo.errors import PyMongoError

from admin import config as configuration
from admin.server import serve
from admin.session import Review, Session
from parsers import card_files
from storage.answers import answered, given
from storage.cards import stored
from storage.mongo import database


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=configuration.DEFAULT_FILE,
                        help="which cards to work on (default: admin/config.json)")
    parser.add_argument("--db", default=None, help="database to write to (default: MONGO_DB)")
    args = parser.parse_args(argv)

    try:
        paths, port = configuration.read(args.config)
        cards = card_files.read(paths)
    except ValueError as error:
        sys.exit(str(error))
    if not cards:
        sys.exit("no cards under: %s" % ", ".join(paths))
    cards.sort(key=lambda card: (card.source, card.date, card.id))

    try:
        with database(args.db) as db:
            session = Session(cards, answered(db))
            progress = session.progress
            print("%d cards, %d already answered, %d to go — writing to %s" % (
                progress["total"], progress["answered"], progress["left"], db.name))
            serve(db, session, lambda: Review(stored(db), given(db)), port)
            print("answered %d, skipped %d, %d left" % (
                session.progress["answered"], session.progress["skipped"], session.progress["left"]))
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
