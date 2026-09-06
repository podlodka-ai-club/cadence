"""Hand cards to the filter-card skill and keep what it says about them.

    python -m judge.run --run NAME [--rules SET] [--answered] [--source S] [--from DATE]
                        [--to DATE] [--limit N] [--batch N] [--parallel N] [--model M]
                        [--db NAME] [--dry-run]

- `--run NAME` — which run the verdicts belong to. `live` is the filter as it
  stands in production; any other name is an evaluation run.
- `--rules SET` — which rules the filter is given, from the `rules`
  collection: `active` (the default) for every active rule, `none` for a run
  without rules, or a comma-separated list of names; `active,NAME` adds a
  candidate to the active ones — how a draft is put through the gate. The
  set is recorded on the run, and a run resumed with a different set is
  refused.
- `--answered` — only cards that have an answer in `answers`: the eval set.
- `--source`, `--from`, `--to` — narrow the cards to one source and a span of
  posting dates (`YYYY-MM-DD`; `--to` is exclusive). Start small: one day, one
  channel.
- `--limit N` — at most this many cards, after the other filters.
- `--batch N` — cards per call to the judge (default 10).
- `--parallel N` — calls in flight at once (default 5).
- `--model M` — the model that judges (default `sonnet`). A verdict is only
  comparable to one from the same model, so every run of a comparison uses
  the same one.
- `--dry-run` — say which cards would be judged, and stop.

Cards come from the `cards` collection; put them there first with
`storage.load_cards` or the online parser. A card that already has a verdict in
this run is skipped, so a run that stopped halfway is finished by running it
again with the same name.

Each batch is written as card files into a temporary directory under the
working material, the rules as one JSON file beside them, and `claude -p` is
asked to run the filter-card skill on those paths. The reply carries the
skill's JSON block; the verdicts in it are checked against the batch — every
card answered, every reason from the closed list, every rule one that was
given — and written. A reply that cannot be read fails the whole batch: nothing
from it is written, and the batch is reported so a rerun picks it up.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from pymongo.errors import PyMongoError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import answers, rules, runs, verdicts
from storage.cards import stored
from storage.mongo import database
from storage.schema import REASONS

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(REPO, "untracked")
DEFAULT_MODEL = "sonnet"
DEFAULT_BATCH = 10
DEFAULT_PARALLEL = 5
BATCH_TIMEOUT = 600  # seconds; a batch of ten should take a minute

JSON_BLOCK = re.compile(r"```json\s*(\[.*?\])\s*```", re.S)


def report(line):
    print("%s %s" % (datetime.now(timezone.utc).strftime("%H:%M:%S"), line), flush=True)


# -- which cards -------------------------------------------------------------

def day(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError("not a date (YYYY-MM-DD): %s" % text)


def select(db, args):
    """The cards this run is asked to judge, minus those it already has."""
    query = {}
    if args.source:
        query["source"] = args.source
    if args.since or args.until:
        span = {}
        if args.since:
            span["$gte"] = args.since
        if args.until:
            span["$lt"] = args.until
        query["date"] = span
    cards = stored(db, query)
    if args.answered:
        eval_set = answers.answered(db)
        cards = [card for card in cards if (card.source, card.id) in eval_set]
    done = verdicts.judged(db, args.run)
    cards = [card for card in cards if (card.source, card.id) not in done]
    if args.limit:
        cards = cards[:args.limit]
    return cards, len(done)


def batches(cards, size):
    return [cards[i:i + size] for i in range(0, len(cards), size)]


# -- which rules -------------------------------------------------------------

def rule_set(db, spec):
    """The rules `--rules` asks for, as stored. `active`, `none`, or names;
    `active` among the names stands for every active rule."""
    chosen = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        if part == "none":
            continue
        if part == "active":
            chosen.extend(rules.with_status(db, "active"))
        else:
            chosen.extend(rules.named(db, [part]))
    seen = set()
    unique = []
    for rule in chosen:
        if rule["name"] not in seen:
            seen.add(rule["name"])
            unique.append(rule)
    return unique


# -- one batch through the judge ---------------------------------------------

def prompt_for(paths, rules_path):
    lines = ["Run the filter-card skill on these card files and return its verdict:"] + list(paths)
    if rules_path:
        lines.append("Judge by the rules in this file as well: %s" % rules_path)
    return "\n".join(lines)


def ask(paths, rules_path, model):
    """One call to the judge. Returns the text of its reply."""
    command = [
        "claude", "-p", prompt_for(paths, rules_path),
        "--model", model,
        "--output-format", "json",
        "--allowedTools", "Read",
    ]
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, timeout=BATCH_TIMEOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError("claude exited %d: %s" % (completed.returncode, completed.stderr.strip()[-500:]))
    envelope = json.loads(completed.stdout)
    if envelope.get("is_error"):
        raise RuntimeError("claude reported an error: %s" % str(envelope.get("result"))[:500])
    return envelope.get("result") or "", envelope


def parse(reply, cards, rule_names=()):
    """The verdicts in a reply, checked against the cards they are about and
    the rules the judge was given."""
    match = JSON_BLOCK.search(reply)
    if not match:
        raise ValueError("no JSON block in the reply")
    try:
        items = json.loads(match.group(1))
    except ValueError as error:
        raise ValueError("the JSON block does not parse: %s" % error)
    expected = {(card.source, card.id): card for card in cards}
    seen = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("a verdict is not an object: %r" % (item,))
        key = (item.get("source"), str(item.get("externalId", "")))
        if key not in expected:
            raise ValueError("a verdict about a card not in the batch: %s/%s" % key)
        if key in seen:
            raise ValueError("two verdicts about %s/%s" % key)
        accept = item.get("accept")
        if not isinstance(accept, bool):
            raise ValueError("%s/%s: accept is not a boolean" % key)
        reasons = item.get("reasons") or []
        unknown = [r for r in reasons if r not in REASONS]
        if unknown:
            raise ValueError("%s/%s: reason outside the list: %s" % (key + (", ".join(unknown),)))
        if not accept and not reasons:
            raise ValueError("%s/%s: refused without a reason" % key)
        applied = item.get("rules") or []
        strange = [r for r in applied if r not in rule_names]
        if strange:
            raise ValueError("%s/%s: rule the judge was not given: %s" % (key + (", ".join(strange),)))
        seen[key] = {
            "source": key[0], "externalId": key[1],
            "accept": accept, "reasons": [] if accept else reasons,
            "note": item.get("note") or None,
            "rules": applied,
        }
    missing = [key for key in expected if key not in seen]
    if missing:
        raise ValueError("no verdict about %s" % ", ".join("%s/%s" % key for key in missing))
    return list(seen.values())


def write_rules(workdir, chosen):
    """The rules as one file the skill reads: name and text, nothing else.
    Returns its path relative to the repository, or None without rules."""
    if not chosen:
        return None
    path = os.path.join(workdir, "rules.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([{"name": r["name"], "text": r["text"]} for r in chosen], fh, ensure_ascii=False, indent=2)
    return os.path.relpath(path, REPO)


def judge_batch(number, cards, model, workdir, rules_path, rule_names):
    """Write one batch as files, ask the judge, return the verdicts and the cost."""
    folder = os.path.join(workdir, "batch-%03d" % number)
    os.makedirs(folder)
    paths = []
    for card in cards:
        path = os.path.join(folder, "%s.json" % card.id)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(card.to_dict(), fh, ensure_ascii=False, indent=2)
        paths.append(os.path.relpath(path, REPO))
    reply, envelope = ask(paths, rules_path, model)
    return parse(reply, cards, rule_names), envelope.get("total_cost_usd") or 0.0


# -- the run -----------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="which run the verdicts belong to; `live` is production")
    parser.add_argument("--rules", default="active", help="rules to judge by: active, none, or names (default: active)")
    parser.add_argument("--answered", action="store_true", help="only cards that have an answer: the eval set")
    parser.add_argument("--source", default=None, help="only cards of this source")
    parser.add_argument("--from", dest="since", type=day, default=None, help="posted on or after this day (YYYY-MM-DD)")
    parser.add_argument("--to", dest="until", type=day, default=None, help="posted before this day (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=0, help="at most this many cards")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="cards per call (default: %d)" % DEFAULT_BATCH)
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help="calls in flight at once (default: %d)" % DEFAULT_PARALLEL)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="the model that judges (default: %s)" % DEFAULT_MODEL)
    parser.add_argument("--db", default=None, help="database to work in (default: MONGO_DB)")
    parser.add_argument("--dry-run", action="store_true", help="say which cards would be judged, and stop")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            try:
                chosen = rule_set(db, args.rules)
            except KeyError as error:
                sys.exit(error.args[0])
            rule_names = [r["name"] for r in chosen]
            cards, done = select(db, args)
            report("run %s in %s: %d cards to judge, %d already judged, rules: %s" % (
                args.run, db.name, len(cards), done, ", ".join(rule_names) or "none"))
            for source in sorted({card.source for card in cards}):
                own = [card for card in cards if card.source == source]
                report("  %-28s %4d cards  %s .. %s" % (source, len(own), own[0].day, own[-1].day))
            if args.dry_run or not cards:
                return
            try:
                runs.begin(db, args.run, args.model, rule_names)
            except ValueError as error:
                sys.exit(str(error))

            work = batches(cards, args.batch)
            started = datetime.now(timezone.utc)
            written = failed = 0
            cost = 0.0
            os.makedirs(SCRATCH, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="judge-", dir=SCRATCH) as workdir:
                rules_path = write_rules(workdir, chosen)
                with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                    futures = {
                        pool.submit(judge_batch, number, batch, args.model, workdir, rules_path, rule_names): (number, batch)
                        for number, batch in enumerate(work, 1)
                    }
                    for future in futures:
                        number, batch = futures[future]
                        try:
                            found, spent = future.result()
                        except Exception as error:  # one batch's failure is that batch's alone
                            failed += 1
                            report("batch %d (%d cards) failed: %s" % (number, len(batch), error))
                            continue
                        verdicts.record(db, args.run, args.model, found)
                        written += len(found)
                        cost += spent
                        accepted = sum(1 for v in found if v["accept"])
                        report("batch %d: %d cards, %d accepted, $%.3f" % (number, len(found), accepted, spent))
            elapsed = datetime.now(timezone.utc) - started
            report("done: %d verdicts written, %d batches failed, $%.3f, %s" % (
                written, failed, cost, str(elapsed - timedelta(microseconds=elapsed.microseconds))))
            if failed:
                report("run again with --run %s to judge what the failed batches left" % args.run)
                sys.exit(1)
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
