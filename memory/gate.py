"""Decide a memory rule, or a schema change, from the observations of the memory
before and after it.

    python -m memory.gate NAME --before INSTANCE_ID --after INSTANCE_ID
                          [--schema] [--db NAME] [--dry-run]

Two memories hold the same set of posts, one written without the rule and one
with it. The rule is judged on its own cards — the ones it was drawn from, and
whatever else was put on it to keep an eye on — by the marks those cards were
given in each memory.

A card is **fixed** when its three marks add up to more than they did, and
**broken** when any one of the three came out lower than before. A rule passes
when it fixed at least one card and broke none: an instruction given to every
post has to be worth something on the posts it is about, and cost nothing on
the rest. It becomes `active`; otherwise `rejected`, and a rejected rule stays
so that it is not proposed again. The numbers go on the rule either way.

`--schema` decides a draft from `schema_changes` instead of a rule from `rules`.
The arithmetic is the same — the two are judged by the same evidence — but they
are kept apart because they are applied differently: a rule is given to whoever
writes one post, a schema change is given to a memory once and holds for
everything written into it afterwards. A schema change is only decided once
whoever runs the loop has said what to write instead.

Only a draft is decided. Nothing here costs xmemory anything: the marks were
paid for when they were made.
"""
import argparse
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import observations, rules, schema_changes
from storage.mongo import database
from storage.schema import OBSERVATION_AXES

TRIPLE = "%s/%s/%s"


def marks(observation):
    """The three marks, as they are printed."""
    return TRIPLE % tuple(observation[axis]["score"] for axis in OBSERVATION_AXES)


def compare(before, after, cards):
    """Every card observed in both memories, and what became of it."""
    both = [key for key in cards if key in before and key in after]
    fixed = [k for k in both if observations.total(after[k]) > observations.total(before[k])]
    broken = [k for k in both
              if any(after[k][axis]["score"] < before[k][axis]["score"] for axis in OBSERVATION_AXES)]
    return both, fixed, broken


def decision(both, fixed, broken):
    """`active` or `rejected`, and the reason in a line."""
    if not both:
        return "rejected", "not one of its cards was observed in both memories"
    if broken:
        return "rejected", "broke %d card(s) of the %d it was judged on" % (len(broken), len(both))
    if not fixed:
        return "rejected", "changed nothing on any of the %d cards" % len(both)
    return "active", "fixed %d of %d cards and broke none" % (len(fixed), len(both))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", metavar="NAME", help="the draft to decide")
    parser.add_argument("--schema", action="store_true",
                        help="decide a schema change rather than a rule")
    parser.add_argument("--before", required=True, metavar="INSTANCE_ID", help="the memory written without the rule")
    parser.add_argument("--after", required=True, metavar="INSTANCE_ID", help="the memory written with it")
    parser.add_argument("--db", default=None, help="database to work in (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true", help="show the decision, write nothing")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            collection = schema_changes if args.schema else rules
            what = "schema change" if args.schema else "rule"
            try:
                judged = collection.named(db, [args.name])[0]
            except KeyError as error:
                sys.exit(error.args[0])
            if not args.schema and judged.get("target") != "memory":
                sys.exit("rule %s is addressed to the filter, and is decided by judge.gate" % args.name)
            if args.schema and not judged.get("change"):
                sys.exit("schema change %s has no decision on it yet: memory.approve says what to "
                         "write instead before it can be judged" % args.name)
            if judged["status"] != "draft":
                sys.exit("%s %s is %s already, not a draft" % (what, args.name, judged["status"]))
            cards = [(card["source"], card["externalId"]) for card in judged["cards"]]
            if not cards:
                sys.exit("%s %s names no card to judge it on" % (what, args.name))

            before = observations.latest(db, args.before, cards)
            after = observations.latest(db, args.after, cards)
            both, fixed, broken = compare(before, after, cards)
            status, why = decision(both, fixed, broken)
            gate = {
                "before": args.before, "after": args.after, "of": len(both),
                "scoreBefore": sum(observations.total(before[k]) for k in both),
                "scoreAfter": sum(observations.total(after[k]) for k in both),
                "fixed": len(fixed), "broken": len(broken),
            }
            print("%s: %s — %s" % (args.name, status, why))
            print("  marks over %d card(s): %d -> %d of %d" % (
                len(both), gate["scoreBefore"], gate["scoreAfter"], len(both) * 15))
            for key in cards:
                if key in both:
                    became = "fixed" if key in fixed else ("broken" if key in broken else "")
                    print("  %-30s %-8s %-8s -> %-8s %s" % (
                        key[0], key[1], marks(before[key]), marks(after[key]), became))
                elif key not in before and key not in after:
                    print("  %-30s %-8s observed in neither memory" % key)
                else:
                    print("  %-30s %-8s not observed in the memory %s" % (
                        key[0], key[1], "after" if key not in after else "before"))
            if args.dry_run:
                print("  nothing written")
                return
            collection.decide(db, args.name, status, gate)
            print("  written")
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
