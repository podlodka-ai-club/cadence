"""The rules drawn from what went wrong, and where each of them stands.

A rule is addressed to one of two readers. A `filter` rule is bound to one
refusal reason and describes the kind of card that reason is wrongly given to;
the filter withholds the reason on such a card and reports the rule's name on
the verdict. A `memory` rule is given to whatever writes a post into memory and
says how to read a post of a certain kind; it names no reason, because there is
no refusal to lift. Nothing here decides which rules anything gets — the caller
does, by target, by status or by name.
"""
from datetime import datetime, timezone

from storage.schema import REASONS, RULE_STATUSES, RULE_TARGETS


def add(db, name, text, target="filter", reason=None, cards=(), proposed_from=None, status="draft"):
    """Write one rule. A second write under the same name replaces the text, the
    cards and the origin, and leaves the status and the gate alone."""
    if status not in RULE_STATUSES:
        raise ValueError("no such status: %s" % status)
    if target not in RULE_TARGETS:
        raise ValueError("no such target: %s" % target)
    if target == "filter" and (reason not in REASONS or reason == "unknown"):
        raise ValueError("not a reason a rule can withhold: %s" % reason)
    if target == "memory" and reason is not None:
        raise ValueError("a memory rule withholds no reason, so it names none")
    fields = {"target": target, "text": text,
              "cards": [{"source": s, "externalId": str(e)} for s, e in cards]}
    if reason is not None:
        fields["reason"] = reason
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


def with_status(db, status, target=None):
    """Every rule in one status, oldest first; of one target when named."""
    query = {"status": status}
    if target is not None:
        query["target"] = target
    return list(db.rules.find(query, {"_id": 0}).sort("proposedAt", 1))


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
