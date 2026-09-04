"""Measure a run: its verdicts against the answers, or against another run.

    python -m judge.report --run NAME [--base RUN] [--out FILE] [--db NAME]

Without `--base`, the run is measured against `answers`: how many cards both
sides judged, how many verdicts agree on `accept`, and the disagreements in
full — the card, what the person said, what the filter said. A card the run
judged that has no answer is counted but not compared.

With `--base RUN`, two runs are measured against the answers side by side, and
the cards on which they differ are listed as fixed (base wrong, run right),
broken (base right, run wrong) or moved (both wrong, differently). This is how
a candidate rule is judged: better than the base on the same answers, and
nothing broken that the rule was not worth.

`--out FILE` writes the same text to a file as well. Listing every run there
is: `python -m judge.report --list`.
"""
import argparse
import os
import sys

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import answers, verdicts
from storage.cards import stored
from storage.mongo import database


def verdict_line(item):
    """`accept`, or `reject — reason, reason`, the way the disagreement doc reads."""
    if item is None:
        return "—"
    if item["accept"]:
        return "accept"
    line = "reject — " + ", ".join(item["reasons"])
    if item.get("note"):
        line += " (%s)" % item["note"]
    return line


def card_block(card, rows):
    """One disagreement, as markdown: the identity, a table of verdicts, the text."""
    out = ["### %s/%s" % (card.source, card.id), "", "| | |", "|---|---|"]
    for label, value in rows:
        out.append("| %s | %s |" % (label, value))
    out.append("| posted | %s |" % card.date.isoformat())
    out += ["", "```", card.text, "```"]
    if card.links:
        out.append("links: " + " ".join(card.links))
    out.append("")
    return "\n".join(out)


def against_answers(db, run):
    """The run measured against the answers. Returns the report text."""
    said = verdicts.given(db, run)
    truth = answers.given(db)
    if not said:
        return "run %s has no verdicts\n" % run
    compared = {key: (truth[key], said[key]) for key in said if key in truth}
    agree = {key for key, (a, v) in compared.items() if a["accept"] == v["accept"]}
    same_reasons = {key for key in agree if set(compared[key][0]["reasons"]) == set(compared[key][1]["reasons"])}
    wrong_accept = [key for key, (a, v) in compared.items() if v["accept"] and not a["accept"]]
    wrong_reject = [key for key, (a, v) in compared.items() if a["accept"] and not v["accept"]]
    cards = {(card.source, card.id): card for card in stored(db)}

    out = [
        "# Run `%s` against the answers" % run,
        "",
        "| | |",
        "|---|---|",
        "| verdicts | %d |" % len(said),
        "| with an answer | %d |" % len(compared),
        "| agree on accept | %d (%.1f%%) |" % (len(agree), 100.0 * len(agree) / len(compared) if compared else 0),
        "| agree on reasons too | %d |" % len(same_reasons),
        "| filter accepted, person refused | %d |" % len(wrong_accept),
        "| filter refused, person accepted | %d |" % len(wrong_reject),
        "",
    ]
    for title, keys in (("The filter accepted, the person refused", wrong_accept),
                        ("The filter refused, the person accepted", wrong_reject)):
        if not keys:
            continue
        out += ["## %s — %d" % (title, len(keys)), ""]
        for key in sorted(keys, key=lambda k: (k[0], cards[k].date)):
            answer, verdict = compared[key]
            out.append(card_block(cards[key], [("person", verdict_line(answer)), ("filter", verdict_line(verdict))]))
    return "\n".join(out)


def against_base(db, run, base):
    """Two runs measured against the answers side by side. Returns the report text."""
    truth = answers.given(db)
    said = verdicts.given(db, run)
    was = verdicts.given(db, base)
    keys = [key for key in truth if key in said and key in was]
    if not keys:
        return "runs %s and %s have no answered card in common\n" % (run, base)

    def right(item, key):
        return item["accept"] == truth[key]["accept"]

    fixed = [k for k in keys if right(said[k], k) and not right(was[k], k)]
    broken = [k for k in keys if right(was[k], k) and not right(said[k], k)]
    moved = [k for k in keys if not right(said[k], k) and not right(was[k], k)
             and (said[k]["accept"], set(said[k]["reasons"])) != (was[k]["accept"], set(was[k]["reasons"]))]
    base_right = sum(1 for k in keys if right(was[k], k))
    run_right = sum(1 for k in keys if right(said[k], k))
    cards = {(card.source, card.id): card for card in stored(db)}

    out = [
        "# Run `%s` against run `%s`" % (run, base),
        "",
        "| | `%s` | `%s` |" % (base, run),
        "|---|---|---|",
        "| answered cards judged by both | %d | %d |" % (len(keys), len(keys)),
        "| agree with the person | %d (%.1f%%) | %d (%.1f%%) |" % (
            base_right, 100.0 * base_right / len(keys), run_right, 100.0 * run_right / len(keys)),
        "",
        "| | |",
        "|---|---|",
        "| fixed — base wrong, run right | %d |" % len(fixed),
        "| broken — base right, run wrong | %d |" % len(broken),
        "| moved — both wrong, differently | %d |" % len(moved),
        "| net | %+d |" % (len(fixed) - len(broken)),
        "",
    ]
    for title, group in (("Fixed", fixed), ("Broken", broken), ("Moved", moved)):
        if not group:
            continue
        out += ["## %s — %d" % (title, len(group)), ""]
        for key in sorted(group, key=lambda k: (k[0], cards[k].date)):
            out.append(card_block(cards[key], [
                ("person", verdict_line(truth[key])),
                ("`%s`" % base, verdict_line(was[key])),
                ("`%s`" % run, verdict_line(said[key])),
            ]))
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=None, help="the run to measure")
    parser.add_argument("--base", default=None, help="measure --run against this run instead of on its own")
    parser.add_argument("--out", default=None, help="write the report to this file as well")
    parser.add_argument("--list", action="store_true", help="list the runs there are, and stop")
    parser.add_argument("--db", default=None, help="database to read (default: MONGO_DB)")
    args = parser.parse_args(argv)
    if not args.list and not args.run:
        parser.error("--run is required unless --list")

    try:
        with database(args.db) as db:
            if args.list:
                for name, count in verdicts.runs(db).items():
                    print("%-24s %5d verdicts" % (name, count))
                return
            text = against_base(db, args.run, args.base) if args.base else against_answers(db, args.run)
    except PyMongoError as error:
        sys.exit("database error: %s" % error)

    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")


if __name__ == "__main__":
    main()
