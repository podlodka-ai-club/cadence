"""The sources being read, and where the reading got to in each of them.

A source is added once and then read for as long as it stays enabled. Its
document holds the name its cards will carry, the moment to start reading
from, and the id of the last post already stored.

The cursor is what makes a restart safe. It moves only after a card is in the
database, never before, so a parser that stops between the two reads one post
a second time — which the upsert on `(source, externalId)` absorbs — instead
of stepping over it.
"""
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc)


def add(db, source, start_at):
    """Add a source unless it is already there. Returns whether it was added."""
    result = db.sources.update_one(
        {"source": source},
        {"$setOnInsert": {"source": source, "enabled": True, "startAt": start_at}},
        upsert=True,
    )
    return result.upserted_id is not None


def active(db):
    """Every source being read, in a settled order."""
    return list(db.sources.find({"enabled": True}).sort("source", 1))


def listed(db):
    """Every source, enabled or not, in a settled order."""
    return list(db.sources.find().sort("source", 1))


def advance(db, source, message_id, at=None):
    """Record that the source has been read as far as `message_id`, and stored."""
    db.sources.update_one(
        {"source": source},
        {"$set": {"lastMessageId": int(message_id), "lastPolledAt": at or now()}},
    )


def polled(db, source, at=None):
    """Record that the source was read, whether or not it had anything new."""
    db.sources.update_one({"source": source}, {"$set": {"lastPolledAt": at or now()}})
