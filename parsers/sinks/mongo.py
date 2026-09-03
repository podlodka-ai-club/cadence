"""A sink that puts each card in the `cards` collection.

One card, one write: a parser reading a source live has to know that a card is
stored before it moves its cursor past the post, and a batch held in memory
cannot tell it that.

The write is the upsert on `(source, externalId)` that `storage.cards` owns, so
a post that arrives twice — read again after a restart, or loaded from an
export and then met online — leaves one card behind.
"""
from parsers.sinks.base import Sink
from storage.cards import upsert


class MongoSink(Sink):
    """Writes cards into the database it is given. Counts new against known."""

    def __init__(self, db):
        self.db = db
        self.added = 0
        self.refreshed = 0

    @property
    def count(self):
        return self.added + self.refreshed

    def send(self, card):
        added, refreshed = upsert(self.db, [card])
        self.added += added
        self.refreshed += refreshed
        return bool(added)
