"""What produced a run's verdicts: the rules the filter was given and the model.

Written once per invocation of the judge. A run that is resumed keeps its
first record: the rules and the model are not allowed to change under a run
half done, so a resumption that names different ones is refused.
"""
from datetime import datetime, timezone


def begin(db, run, model, rule_names):
    """Record that a run starts, or continues, with these rules and this model."""
    now = datetime.now(timezone.utc)
    existing = db.runs.find_one({"run": run}, {"_id": 0})
    if existing is None:
        db.runs.insert_one({"run": run, "model": model, "rules": list(rule_names), "startedAt": now, "lastAt": now})
        return
    if existing["model"] != model or list(existing["rules"]) != list(rule_names):
        raise ValueError("run %s was started with model %s and rules [%s]; continue it with the same, or name a new run" % (
            run, existing["model"], ", ".join(existing["rules"]) or "none"))
    db.runs.update_one({"run": run}, {"$set": {"lastAt": now}})


def described(db, run):
    """The record of one run, or None when the run has none."""
    return db.runs.find_one({"run": run}, {"_id": 0})
