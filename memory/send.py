"""Write the cards of a set into an xmemory instance, one at a time, in order.

    python -m memory.send SET INSTANCE_ID [--rules NAME,…] [--from N] [--db NAME]

- `SET` — a named set from the `sets` collection. Its cards go in the order the
  set holds them, which matters: a later post merging onto an earlier one is
  part of what is being written, so the order has to be the same in every
  instance the set is written into.
- `INSTANCE_ID` — the xmemory instance to write into. `xmemcli` takes it, so no
  MCP server has to be registered for this to run.
- `--rules NAME,…` — memory rules from the `rules` collection, by name. Their
  texts ride in the wrapper of every card of the set, identically worded: an
  instruction to whatever reads the post, given the same way to all of it, so
  that what it does to a card it was not drawn from is visible too.
- `--from N` — start at the Nth card, for a send that stopped halfway.

Each card is sent in a wrapper naming where it came from, when it was
published, and the city and time offset to read its dates in — memory is given
the post, not the database's idea of it. Writes are synchronous and sequential.
Nothing is judged here: the log says what was sent and what came back.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import rules as rules_collection
from storage import sets
from storage.mongo import database

TIMEOUT = 900

WRAPPER = """Пост из Telegram-канала %(source)s, номер поста %(external_id)s.
Опубликован %(published)s. Город — Санкт-Петербург, часовое смещение +03:00.
%(rules)s
Текст поста:
%(text)s"""


def instruction(rules):
    """The rules as they ride in the wrapper, or nothing at all when there are none."""
    if not rules:
        return ""
    return "\nПравила разбора:\n%s\n" % "\n".join("- %s" % rule["text"] for rule in rules)


def send(text, instance):
    """Write one card. Returns what came back and how long it took."""
    started = time.time()
    completed = subprocess.run(
        ["xmemcli", "--json", "--instance-id", instance, "write", text],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    elapsed = time.time() - started
    try:
        answer = json.loads(completed.stdout)
    except ValueError:
        return {"status": "unreadable", "stderr": completed.stderr.strip()[-300:],
                "stdout": completed.stdout.strip()[-300:]}, elapsed
    return answer, elapsed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("set", metavar="SET", help="the set of cards to write")
    parser.add_argument("instance", metavar="INSTANCE_ID", help="the xmemory instance to write into")
    parser.add_argument("--rules", default=None, help="memory rules to put in the wrapper, by name, comma separated")
    parser.add_argument("--from", dest="start", type=int, default=1, help="start at this card of the set")
    parser.add_argument("--db", default=None, help="database to read the cards from (default: MONGO_DB)")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            try:
                members = sets.members(db, args.set)
            except KeyError as error:
                sys.exit(error.args[0])
            wanted = []
            if args.rules:
                try:
                    wanted = rules_collection.named(db, [n.strip() for n in args.rules.split(",")])
                except KeyError as error:
                    sys.exit(error.args[0])
                other = [rule["name"] for rule in wanted if rule.get("target") != "memory"]
                if other:
                    sys.exit("not a rule memory is given: %s" % ", ".join(other))
            cards = {}
            for document in db.cards.find(
                    {"$or": [{"source": s, "externalId": e} for s, e in members]}, {"_id": 0}):
                cards[(document["source"], document["externalId"])] = document
    except PyMongoError as error:
        sys.exit("database error: %s" % error)

    missing = [key for key in members if key not in cards]
    if missing:
        sys.exit("no card for %s" % ", ".join("%s/%s" % key for key in missing))

    rules_text = instruction(wanted)
    print("%s: %d cards → %s%s" % (
        args.set, len(members), args.instance,
        ", with %s" % ", ".join(rule["name"] for rule in wanted) if wanted else ", no rules"), flush=True)
    if rules_text:
        print(rules_text.strip(), flush=True)

    failed = []
    for number, key in enumerate(members, 1):
        if number < args.start:
            continue
        card = cards[key]
        text = WRAPPER % {
            "source": card["source"],
            "external_id": card["externalId"],
            "published": card["date"].astimezone(timezone.utc).isoformat(),
            "rules": rules_text,
            "text": card["text"],
        }
        answer, elapsed = send(text, args.instance)
        status = "ok" if answer.get("write_id") else (answer.get("status") or "error")
        print("%s %2d/%d %-30s %-8s %-8s %-38s %s  %.0fs" % (
            datetime.now().strftime("%H:%M:%S"), number, len(members),
            card["source"], card["externalId"], status,
            str(answer.get("write_id"))[:38],
            ", ".join(answer.get("extracted") or []), elapsed), flush=True)
        if status != "ok":
            failed.append(key)
            print("     %s" % json.dumps(answer, ensure_ascii=False)[:600], flush=True)

    print("done: %d sent, %d not ok" % (len(members) - args.start + 1, len(failed)), flush=True)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
