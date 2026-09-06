"""Decide a candidate rule from a run with it against a run without it.

    python -m judge.gate --rule NAME --run RUN --base BASE [--db NAME] [--dry-run]

`RUN` is the run that was given the candidate, `BASE` the same cards judged
without it. The rule is judged on the cards it fired on — those whose verdict
in `RUN` names it — because two runs of the same judge differ on a few cards
of every hundred by themselves, and a rule's effect would drown in that. It
passes when it fixed more of those cards than it broke and broke none on
`accept` itself: a rule may cost a reason here and there for a larger gain,
but not turn a right accept or a right refusal into a wrong one. It becomes
`active`; otherwise `rejected`. Either way the numbers are written on the
rule, the whole-set agreement beside the rule's own.

Only a `draft` is decided. `--dry-run` shows the decision and writes nothing.
"""
import argparse
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from judge.report import compare
from storage import rules, runs
from storage.mongo import database


def by_rule(found, rule):
    """The comparison narrowed to the cards whose candidate verdict names the rule."""
    fired = [k for k in found["keys"] if rule in found["said"][k]["rules"]]
    own = set(fired)
    return {
        "fired": fired,
        "fixed": [k for k in found["fixed"] if k in own],
        "broken": [k for k in found["broken"] if k in own],
        "broken_accept": [k for k in found["broken_accept"] if k in own],
    }


def decision(own):
    """`active` or `rejected`, and the reason in a line."""
    gain = len(own["fixed"]) - len(own["broken"])
    if not own["fired"]:
        return "rejected", "fired on no card"
    if own["broken_accept"]:
        return "rejected", "breaks %d card(s) on accept" % len(own["broken_accept"])
    if gain <= 0:
        return "rejected", "net %+d on its own cards, no gain" % gain
    return "active", "net %+d on its own cards, nothing broken on accept" % gain


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rule", required=True, help="the draft rule to decide")
    parser.add_argument("--run", required=True, help="the run that was given the rule")
    parser.add_argument("--base", required=True, help="the same cards judged without it")
    parser.add_argument("--db", default=None, help="database to work in (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true", help="show the decision, write nothing")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            try:
                rule = rules.named(db, [args.rule])[0]
            except KeyError as error:
                sys.exit(error.args[0])
            if rule["status"] != "draft":
                sys.exit("rule %s is %s already, not a draft" % (rule["name"], rule["status"]))
            for name, must_have in ((args.run, True), (args.base, False)):
                record = runs.described(db, name)
                if record is None:
                    sys.exit("run %s has no record of what it was given" % name)
                if (args.rule in record["rules"]) != must_have:
                    sys.exit("run %s %s the rule %s" % (name, "was not given" if must_have else "was given", args.rule))
            found = compare(db, args.run, args.base)
            if found is None:
                sys.exit("runs %s and %s have no answered card in common" % (args.run, args.base))
            own = by_rule(found, args.rule)
            status, why = decision(own)
            gate = {
                "run": args.run, "base": args.base, "of": len(found["keys"]),
                "agreeBefore": found["base_right"], "agreeAfter": found["run_right"],
                "fired": len(own["fired"]), "fixed": len(own["fixed"]), "broken": len(own["broken"]),
                "brokenOnAccept": len(own["broken_accept"]),
            }
            print("%s: %s — %s" % (args.rule, status, why))
            print("  fired on %d of %d cards: fixed %d, broke %d (%d on accept)" % (
                gate["fired"], gate["of"], gate["fixed"], gate["broken"], gate["brokenOnAccept"]))
            print("  whole set: agree %d -> %d; every difference between the runs: fixed %d, broken %d" % (
                gate["agreeBefore"], gate["agreeAfter"], len(found["fixed"]), len(found["broken"])))
            for title in ("fixed", "broken"):
                for key in own[title]:
                    print("  %-6s %s/%s" % (title, key[0], key[1]))
            if args.dry_run:
                return
            rules.decide(db, args.rule, status, gate)
            print("  written")
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
