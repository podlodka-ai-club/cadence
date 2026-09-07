"""How a post landed in one memory, as an observer saw it.

One record is one observation of one card in one instance: three marks — the
times the event is held, the event itself, the venue — with what each is blamed
on and why it was given. Nothing here is a right answer given by a person; the
observer held the post against what memory returned, and the marks say how far
apart the two were.

The same card observed in two instances makes two records, which is what a rule
is judged on. The same card observed twice in one instance makes two as well —
re-checking a mark that looked wrong is data too — so a reader takes the latest
by `observedAt`.
"""
from datetime import datetime, timezone

from storage.schema import OBSERVATION_AXES


def record(db, instance, set_name, source, external_id, marks,
           model, cost_usd=None, seconds=None, observed_at=None):
    """Write one observation. `marks` is what the observer returned: a mark for
    each axis, what it asked, and its proposal."""
    missing = [axis for axis in OBSERVATION_AXES if axis not in marks]
    if missing:
        raise ValueError("the observation has no %s" % ", ".join(missing))
    document = {
        "instance": instance,
        "set": set_name,
        "source": source,
        "externalId": str(external_id),
        "model": model,
        "observedAt": observed_at or datetime.now(timezone.utc),
    }
    for axis in OBSERVATION_AXES:
        mark = marks[axis]
        document[axis] = {
            "score": int(mark["score"]),
            "labels": list(mark.get("labels") or []),
            "why": mark["why"],
        }
    if marks.get("asked"):
        document["asked"] = list(marks["asked"])
    if "proposal" in marks:
        document["proposal"] = marks["proposal"]
    if cost_usd is not None:
        document["costUsd"] = float(cost_usd)
    if seconds is not None:
        document["seconds"] = int(seconds)
    db.observations.insert_one(document)
    return document


def latest(db, instance, cards=None):
    """The newest observation of each card in an instance, keyed by
    `(source, externalId)`. `cards` narrows it to those pairs."""
    query = {"instance": instance}
    if cards is not None:
        cards = [(s, str(e)) for s, e in cards]
        if not cards:
            return {}
        query["$or"] = [{"source": s, "externalId": e} for s, e in cards]
    newest = {}
    for document in db.observations.find(query, {"_id": 0}).sort("observedAt", 1):
        newest[(document["source"], document["externalId"])] = document
    return newest


def every(db, instance=None):
    """Every observation, oldest first; of one instance when named."""
    query = {"instance": instance} if instance else {}
    return list(db.observations.find(query, {"_id": 0}).sort("observedAt", 1))


def total(mark_holder):
    """The three marks of one observation added up, out of fifteen."""
    return sum(mark_holder[axis]["score"] for axis in OBSERVATION_AXES)
