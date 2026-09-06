"""The rules the filter is given, and where each of them stands.

A rule is a plain-language instruction with a name. The filter is handed the
text and reports the name back on every verdict the rule reached; nothing here
decides which rules a run gets — the caller does, by status or by name.
"""
from datetime import datetime, timezone

from storage.schema import RULE_STATUSES


def add(db, name, text, cards=(), proposed_from=None, status="draft"):
    """Write one rule. A second write under the same name replaces the text,
    the cards and the origin, and leaves the status and the gate alone."""
    if status not in RULE_STATUSES:
        raise ValueError("no such status: %s" % status)
    fields = {"text": text, "cards": [{"source": s, "externalId": str(e)} for s, e in cards]}
    if proposed_from:
        fields["proposedFrom"] = proposed_from
    db.rules.update_one(
        {"name": name},
        {"$set": fields,
         "$setOnInsert": {"name": name, "status": status, "proposedAt": datetime.now(timezone.utc)}},
        upsert=True,
    )


def decide(db, name, status, gate=None):
    """Move a rule to `active` or `rejected`, with the numbers the gate saw."""
    if status not in RULE_STATUSES:
        raise ValueError("no such status: %s" % status)
    fields = {"status": status, "decidedAt": datetime.now(timezone.utc)}
    if gate is not None:
        fields["gate"] = gate
    result = db.rules.update_one({"name": name}, {"$set": fields})
    if result.matched_count == 0:
        raise KeyError("no rule named %s" % name)


def with_status(db, status):
    """Every rule in one status, oldest first."""
    return list(db.rules.find({"status": status}, {"_id": 0}).sort("proposedAt", 1))


def named(db, names):
    """The rules with these names, in the order the names were given.
    Raises KeyError for a name there is no rule for."""
    found = {rule["name"]: rule for rule in db.rules.find({"name": {"$in": list(names)}}, {"_id": 0})}
    missing = [name for name in names if name not in found]
    if missing:
        raise KeyError("no rule named %s" % ", ".join(missing))
    return [found[name] for name in names]


def every(db):
    """Every rule, oldest first."""
    return list(db.rules.find({}, {"_id": 0}).sort("proposedAt", 1))
