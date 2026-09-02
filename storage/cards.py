"""Putting cards in, and asking what is already there.

A card is addressed by `(source, externalId)` and written with an upsert, so
the same card written twice leaves one copy. Writing it again refreshes the
post itself — its text, its links, its date — and touches nothing else, so an
answer already given about a card survives a rewrite of the card.
"""
from pymongo import UpdateOne

from parsers.card import Card


def upsert(db, cards):
    """Write every card. Returns how many were new and how many were already there."""
    operations = [
        UpdateOne(
            {"source": card.source, "externalId": card.id},
            {
                "$set": {"date": card.date, "text": card.text, "links": list(card.links)},
                "$setOnInsert": {"source": card.source, "externalId": card.id},
            },
            upsert=True,
        )
        for card in cards
    ]
    if not operations:
        return 0, 0
    result = db.cards.bulk_write(operations, ordered=False)
    return len(result.upserted_ids), len(operations) - len(result.upserted_ids)


def stored(db):
    """Every card in the collection, as cards again, in a settled order."""
    return [
        Card(
            id=document["externalId"],
            source=document["source"],
            date=document["date"],
            text=document["text"],
            links=tuple(document.get("links") or ()),
        )
        for document in db.cards.find().sort([("source", 1), ("date", 1), ("externalId", 1)])
    ]
