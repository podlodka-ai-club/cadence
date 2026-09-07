"""Changes to the schema a memory was given, and where each of them stands.

A rule is given to whoever writes one post; a schema change is given to a
memory once and holds for everything written into it afterwards. The two are
proposed from the same evidence and judged by the same numbers, and they are
kept apart so that neither is ever applied as the other.

`finding` is what was diagnosed — which sentence of the schema causes the fault,
and why no instruction could correct it. `change` is what a person decided to
write instead, and only a person writes it: a draft with no `change` is a
question still waiting for an answer.
"""
from datetime import datetime, timezone

from storage.schema import RULE_STATUSES


def add(db, name, instance, finding, cards=(), object_name=None, field=None, proposed_from=None):
    """Write a draft: what was found, on which cards, in which memory. A second
    write under the same name replaces the finding and leaves everything a
    person has since decided alone."""
    fields = {
        "instance": instance,
        "finding": finding,
        "cards": [{"source": s, "externalId": str(e)} for s, e in cards],
    }
    if object_name:
        fields["object"] = object_name
    if field:
        fields["field"] = field
    if proposed_from:
        fields["proposedFrom"] = proposed_from
    db.schema_changes.update_one(
        {"name": name},
        {"$set": fields,
         "$setOnInsert": {"name": name, "status": "draft", "proposedAt": datetime.now(timezone.utc)}},
        upsert=True,
    )


def approve(db, name, change):
    """Say what to write instead. This is the person's word, and nothing is
    decided before it: the gate has nothing to judge until a memory has been
    written under it."""
    result = db.schema_changes.update_one(
        {"name": name},
        {"$set": {"change": change, "approvedAt": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        raise KeyError("no schema change named %s" % name)


def decide(db, name, status, gate=None):
    """Move it to `active` or `rejected`, with the numbers the gate saw."""
    if status not in RULE_STATUSES:
        raise ValueError("no such status: %s" % status)
    fields = {"status": status, "decidedAt": datetime.now(timezone.utc)}
    if gate is not None:
        fields["gate"] = gate
    result = db.schema_changes.update_one({"name": name}, {"$set": fields})
    if result.matched_count == 0:
        raise KeyError("no schema change named %s" % name)


def named(db, names):
    """The changes with these names, in the order the names were given."""
    found = {c["name"]: c for c in db.schema_changes.find({"name": {"$in": list(names)}}, {"_id": 0})}
    missing = [name for name in names if name not in found]
    if missing:
        raise KeyError("no schema change named %s" % ", ".join(missing))
    return [found[name] for name in names]


def with_status(db, status):
    """Every change in one status, oldest first."""
    return list(db.schema_changes.find({"status": status}, {"_id": 0}).sort("proposedAt", 1))


def every(db):
    """Every change, oldest first."""
    return list(db.schema_changes.find({}, {"_id": 0}).sort("proposedAt", 1))
