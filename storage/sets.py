"""Named sets of cards to judge, and the cards in one.

A set is written once and not edited afterwards: two runs over the same set
are comparable because the cards underneath them did not move. Choosing
differently means writing another set under another name.
"""
from datetime import datetime, timezone


def define(db, name, cards, note=None):
    """Write a set. Refuses a name that is already taken — a set is not edited.

    `cards` are `(source, externalId, why)` in the order they were chosen,
    `why` being the labels saying what each card is in the set for."""
    if db.sets.find_one({"name": name}, {"_id": 1}):
        raise ValueError("a set named %s already exists, and a set is not edited" % name)
    document = {
        "name": name,
        "cards": [
            {"source": source, "externalId": str(external_id), "why": list(why)}
            for source, external_id, why in cards
        ],
        "createdAt": datetime.now(timezone.utc),
    }
    if note:
        document["note"] = note
    db.sets.insert_one(document)


def members(db, name):
    """Every `(source, externalId)` in the set, in the order it was written.
    Raises KeyError for a name there is no set for."""
    document = db.sets.find_one({"name": name}, {"_id": 0, "cards": 1})
    if document is None:
        raise KeyError("no set named %s" % name)
    return [(card["source"], card["externalId"]) for card in document["cards"]]


def named(db, name):
    """The whole set, `why` and all."""
    document = db.sets.find_one({"name": name}, {"_id": 0})
    if document is None:
        raise KeyError("no set named %s" % name)
    return document


def every(db):
    """Every set, oldest first."""
    return list(db.sets.find({}, {"_id": 0}).sort("createdAt", 1))
