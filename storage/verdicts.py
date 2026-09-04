"""Recording what the filter said about a card, and reading it back by run.

A verdict belongs to a card and to a run. Writing the same `(run, card)` twice
replaces the first verdict rather than adding a second, so a run can be
resumed — or the `live` run refreshed — without leaving two opinions behind.
"""
from datetime import datetime, timezone

from pymongo import UpdateOne


def record(db, run, model, verdicts):
    """Write the verdicts of one run. Each is a dict with `source`, `externalId`,
    `accept`, `reasons`, and optionally `note` and `rules`."""
    now = datetime.now(timezone.utc)
    operations = []
    for verdict in verdicts:
        fields = {
            "accept": bool(verdict["accept"]),
            "reasons": [] if verdict["accept"] else list(verdict["reasons"]),
            "rules": list(verdict.get("rules") or []),
            "model": model,
            "judgedAt": now,
        }
        unset = {}
        if verdict.get("note"):
            fields["note"] = verdict["note"]
        else:
            unset["note"] = ""
        update = {
            "$set": fields,
            "$setOnInsert": {"run": run, "source": verdict["source"], "externalId": verdict["externalId"]},
        }
        if unset:
            update["$unset"] = unset
        operations.append(UpdateOne(
            {"run": run, "source": verdict["source"], "externalId": verdict["externalId"]},
            update,
            upsert=True,
        ))
    if operations:
        db.verdicts.bulk_write(operations, ordered=False)
    return len(operations)


def given(db, run):
    """Every verdict of one run, by the card it is about."""
    return {
        (document["source"], document["externalId"]): {
            "accept": document["accept"],
            "reasons": list(document["reasons"]),
            "note": document.get("note"),
            "rules": list(document.get("rules") or []),
            "model": document["model"],
        }
        for document in db.verdicts.find({"run": run}, {"_id": 0})
    }


def judged(db, run):
    """Every `(source, externalId)` that already has a verdict in this run."""
    return {
        (document["source"], document["externalId"])
        for document in db.verdicts.find({"run": run}, {"_id": 0, "source": 1, "externalId": 1})
    }


def runs(db):
    """Every run name that has at least one verdict, with how many."""
    return {
        row["_id"]: row["n"]
        for row in db.verdicts.aggregate([{"$group": {"_id": "$run", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}])
    }
