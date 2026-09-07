"""Draft a memory rule from what the observations of one instance complain about.

    python -m memory.propose INSTANCE_ID --name NAME [--set NAME] [--label AXIS/LABEL]
                             [--text FILE] [--model M] [--db NAME] [--dry-run]

The observers marked each card on its own and none of them saw another's work.
Where many of them blame the same thing, that thing is a defect of how memory
reads posts rather than an accident of one post — and it is what a rule should
be about. This takes the label blamed on most cards, hands the sentences those
observers wrote to a model, and keeps what it writes as a draft rule in the
`rules` collection, addressed to memory.

- `INSTANCE_ID` — the memory whose observations to read; the latest mark of each
  card counts, so a card observed twice is judged by the second look.
- `--name NAME` — what the draft is called. An existing rule of that name is
  replaced while it is still a draft, and refused once it has been decided.
- `--set NAME` — only observations made over that set.
- `--label AXIS/LABEL` — the label to draft about, instead of the one blamed
  most; repeatable, for a defect that shows itself under more than one label.
- `--text FILE` — take the rule from this file instead of asking a model. The
  drawing of cards and numbers is the same; only the wording is a person's.
- `--dry-run` — print the draft and write nothing.

The skill is given two things: the complaints, and the schema the instance was
created with — what memory was told to keep, which bounds what any instruction
can ask of it. It answers with one of two things, and they are kept in different
collections because they are applied in different ways: a rule, which rides in
the wrapper of every post and goes to `rules`; or a finding that no instruction
could help and the schema itself is at fault, which goes to `schema_changes` as
a draft and waits for a person to say what to write instead.

The wording is the `propose-rule` skill's work, in a session of its own; this
module chooses the complaint, hands them over and keeps what comes back. Like
every session started in this repository, it reads the instructions here and
stops to ask about an uncommitted change instead of working, so the tree has to
be clean — unless the wording comes from `--text`, which starts no session.

Nothing here costs xmemory anything: it reads marks already paid for.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import observations, rules, schema_changes
from storage.mongo import database
from storage.schema import OBSERVATION_AXES

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
TIMEOUT = 600

PROMPT = """Run the propose-rule skill on the schema and the complaints below.

The schema memory was given:

<<SCHEMA>>

The complaints:

<<COMPLAINTS>>
"""


def complaints(latest):
    """The cards blamed on each `(axis, label)`, `other` left out: it means the
    list of labels is short, and two `other`s are not the same complaint."""
    blamed = {}
    for key, observation in latest.items():
        for axis in OBSERVATION_AXES:
            if observation[axis]["score"] == 5:
                continue
            for label in observation[axis]["labels"]:
                if label != "other":
                    blamed.setdefault((axis, label), []).append(key)
    return blamed


def dominant(blamed):
    """The label blamed on most cards. A tie goes to the earliest axis: an event
    with no occurrence takes its place down with it, so what is wrong is the
    schedule rather than the two that follow from it."""
    order = {axis: number for number, axis in enumerate(OBSERVATION_AXES)}
    return min(blamed, key=lambda pair: (-len(blamed[pair]), order[pair[0]], pair[1]))


def material(latest, axis_labels, cards):
    """What the observers said about those cards, for the model to read."""
    lines = []
    for key in cards:
        observation = latest[key]
        for axis, label in axis_labels:
            mark = observation[axis]
            if label in mark["labels"]:
                lines.append("- %s/%s — %s: %s" % (key[0], key[1], axis, mark["why"]))
        if observation.get("proposal"):
            lines.append("  what to do instead: %s" % observation["proposal"])
    return "\n".join(lines)


def schema_of(instance):
    """The schema the instance was created with, as it stands now. The skill is
    given it rather than sent to look for it: what memory was told to do is an
    argument of the question, and a session with no way to read anything can
    read nothing it was not handed."""
    handle, path = tempfile.mkstemp(suffix=".yaml")
    os.close(handle)
    try:
        completed = subprocess.run(
            ["xmemcli", "--instance-id", instance, "schema", "get", "-o", path],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        if completed.returncode != 0:
            raise SystemExit("xmemcli could not get the schema of %s: %s" % (
                instance, (completed.stderr or completed.stdout).strip()[-400:]))
        return open(path, encoding="utf-8").read()
    finally:
        os.unlink(path)


def write_rule(schema, complaint, model):
    """Hand the schema and the complaints to the propose-rule skill, and return
    the verdict and the text it came back with. How a rule is worded is the
    skill's business and not this module's: it is the part meant to get better,
    and it gets better as a skill rather than as a string in here."""
    prompt = PROMPT.replace("<<SCHEMA>>", schema).replace("<<COMPLAINTS>>", complaint)
    completed = subprocess.run(
        ["claude", "-p", prompt, "--model", model,
         "--output-format", "json", "--allowedTools", "Skill"],
        cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT,
    )
    if completed.returncode != 0:
        raise SystemExit("claude exited %d: %s" % (completed.returncode, completed.stderr.strip()[-400:]))
    reply = (json.loads(completed.stdout).get("result") or "").strip()
    found = JSON_BLOCK.search(reply)
    if not found:
        raise SystemExit("no JSON block in the reply: %s" % reply[-600:])
    answer = json.loads(found.group(1))
    return answer.get("verdict"), (answer.get("text") or "").strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance", metavar="INSTANCE_ID", help="the memory whose observations to read")
    parser.add_argument("--name", required=True, help="what the draft rule is called")
    parser.add_argument("--set", dest="set_name", default=None, help="only observations made over this set")
    parser.add_argument("--label", action="append", default=[], metavar="AXIS/LABEL",
                        help="draft about this label instead of the one blamed most")
    parser.add_argument("--control", default=None, metavar="S/N,…",
                        help="cards to judge the rule on besides the ones it was drawn from")
    parser.add_argument("--text", default=None, metavar="FILE", help="take the rule's text from this file")
    parser.add_argument("--model", default="sonnet", help="the model that words the rule (default: sonnet)")
    parser.add_argument("--db", default=None, help="database to work in (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true", help="print the draft, write nothing")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            standing = db.rules.find_one({"name": args.name}, {"_id": 0, "status": 1})
            if standing and standing["status"] != "draft":
                sys.exit("rule %s is %s already, and a decided rule is not redrafted"
                         % (args.name, standing["status"]))
            latest = observations.latest(db, args.instance)
            if args.set_name:
                latest = {key: o for key, o in latest.items() if o["set"] == args.set_name}
            if not latest:
                sys.exit("no observations of instance %s" % args.instance)

            blamed = complaints(latest)
            if not blamed:
                sys.exit("%d cards observed and nothing blamed on any of them" % len(latest))
            print("%d cards observed, %d of them blamed for something:" % (
                len(latest), len({k for keys in blamed.values() for k in keys})))
            for pair in sorted(blamed, key=lambda p: -len(blamed[p])):
                print("  %-9s %-20s %d cards" % (pair[0], pair[1], len(blamed[pair])))

            if args.label:
                wanted = []
                for name in args.label:
                    axis, _, label = name.partition("/")
                    if (axis, label) not in blamed:
                        sys.exit("nothing is blamed on %s" % name)
                    wanted.append((axis, label))
            else:
                wanted = [dominant(blamed)]
            cards = [key for key in latest if any(key in blamed[pair] for pair in wanted)]
            print("\ndrafting about %s, on %d cards" % (
                " and ".join("%s/%s" % pair for pair in wanted), len(cards)))

            controls = []
            if args.control:
                controls = [tuple(part.strip().rsplit("/", 1)) for part in args.control.split(",")]
            drawn_from = "instance %s · %s · %d cards" % (
                args.instance, " and ".join("%s/%s" % pair for pair in wanted), len(cards))

            if args.text:
                verdict, text = "rule", open(args.text, encoding="utf-8").read().strip()
            else:
                verdict, text = write_rule(schema_of(args.instance),
                                           material(latest, wanted, cards), args.model)
            if not text:
                sys.exit("nothing came back to make a rule of")
            if verdict == "schema":
                print("\nno rule: the fault is in the schema, and a person decides what to do\n")
                print(text)
                print("\ncards: %s" % ", ".join("%s/%s" % key for key in cards + controls))
                if args.dry_run:
                    print("\nnothing written")
                    return
                schema_changes.add(db, args.name, args.instance, text, cards=cards + controls,
                                   proposed_from=drawn_from)
                print("\nwritten as a draft in schema_changes — it waits for a person to say what")
                print("to write instead, and is judged once a memory has been written under it")
                return
            if verdict != "rule":
                sys.exit("the skill answered neither rule nor schema, but %r" % verdict)

            print("\n%s (draft, target memory)\n%s\n" % (args.name, text))
            print("cards: %s" % ", ".join("%s/%s" % key for key in cards + controls))
            print("from:  %s" % drawn_from)
            if args.dry_run:
                print("\nnothing written")
                return
            rules.add(db, args.name, text, target="memory", cards=cards + controls,
                      proposed_from=drawn_from)
            print("\nwritten as a draft")
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
