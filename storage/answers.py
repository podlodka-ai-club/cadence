"""Recording the answer about a card, and asking which cards have one.

An answer belongs to the card it is about, addressed the same way, and there
is one per card: answering again replaces the previous answer rather than
adding a second.
"""
from datetime import datetime, timezone


def record(db, source, external_id, accept, reasons):
    """Write the answer about one card. Reasons belong to a refusal only."""
    reasons = [] if accept else list(reasons)
    db.answers.update_one(
        {"source": source, "externalId": external_id},
        {
            "$set": {
                "accept": bool(accept),
                "reasons": reasons,
                "answeredAt": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"source": source, "externalId": external_id},
        },
        upsert=True,
    )


def given(db):
    """Every answer, by the card it is about."""
    return {
        (document["source"], document["externalId"]):
            {"accept": document["accept"], "reasons": list(document["reasons"])}
        for document in db.answers.find({}, {"_id": 0})
    }


def answered(db):
    """Every `(source, externalId)` that already has an answer."""
    return set(given(db))
