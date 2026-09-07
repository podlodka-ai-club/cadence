"""Mark how the cards of a set landed in one memory, a session per card.

    python -m memory.observe SET SERVER INSTANCE_ID [--limit N] [--cards S/N,…]
                             [--seed N] [--model M] [--parallel N] [--db NAME]

- `SET` — the set whose cards were written into the instance.
- `SERVER` — the MCP server the instance answers on, e.g. `xmemory-a-run`. The
  observer questions memory through it.
- `INSTANCE_ID` — the same instance by its id, which is what the marks are
  written under. Two marks of one card belong to different memories, and only
  the id says which.
- `--limit N` — that many cards of the set, chosen at random; `--seed` fixes the
  choice so it can be made again.
- `--cards S/N,…` — exactly these cards, as `source/number`. This is how the
  same cards are observed in a second instance.
- `--model M` — the model that observes (default `sonnet`). Two marks are
  comparable only from the same one.
- `--parallel N` — sessions at once (default 4).

Each card gets its own `claude -p` carrying out the `observe-record` skill: no
shared context, so what one observer saw does not help the next. It is allowed
two things — reading the instance, and printing the post — and writes nothing
itself. The marks it returns go into the `observations` collection; the log says
what each card scored, what it cost and how long it took.

Every session reads this repository's instructions like any other, so the
working tree has to be clean before a run: on an uncommitted change the observer
stops to ask about it instead of observing, and every card comes back empty.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pymongo.errors import PyMongoError, WriteError

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import observations, sets
from storage.mongo import database

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
TIMEOUT = 900

PROMPT = """Run the observe-record skill on this post: %(source)s %(external_id)s

The memory to look in is the xmemory instance behind the `mcp__%(server)s__read` tool.
Read a post with this exact command, from the repository root:

    %(python)s -m storage.show_card SOURCE NUMBER
"""


def interpreter():
    """The command the observer is told to read a post with: this interpreter,
    named from the repository root if it lives inside it."""
    inside = os.path.relpath(sys.executable, REPO)
    return inside if not inside.startswith(os.pardir) else sys.executable


def observe(source, external_id, server, model):
    """One session over one card. Returns what it returned and what it cost."""
    prompt = PROMPT % {"source": source, "external_id": external_id,
                       "server": server, "python": interpreter()}
    started = time.time()
    completed = subprocess.run(
        ["claude", "-p", prompt, "--model", model, "--output-format", "json",
         "--allowedTools", "mcp__%s__read,Bash(%s -m storage.show_card:*)" % (server, interpreter())],
        cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT,
    )
    elapsed = time.time() - started
    if completed.returncode != 0:
        return {"error": "claude exited %d: %s" % (
            completed.returncode, completed.stderr.strip()[-400:])}, elapsed
    envelope = json.loads(completed.stdout)
    reply = envelope.get("result") or ""
    record = {"cost_usd": envelope.get("total_cost_usd")}
    match = JSON_BLOCK.search(reply)
    if not match:
        record["error"] = "no JSON block in the reply"
        record["reply"] = reply[-1500:]
        return record, elapsed
    try:
        record["marks"] = json.loads(match.group(1))
    except ValueError as error:
        record["error"] = "the JSON block does not parse: %s" % error
        record["reply"] = reply[-1500:]
    return record, elapsed


def chosen(members, cards, limit, seed):
    """The cards to observe: those named, or that many at random, or all of them."""
    if cards:
        wanted = [tuple(part.strip().rsplit("/", 1)) for part in cards.split(",")]
        by_number = {(s, e): None for s, e in members}
        missing = [w for w in wanted if w not in by_number]
        if missing:
            sys.exit("not in the set: %s" % ", ".join("%s/%s" % w for w in missing))
        return [m for m in members if m in set(wanted)]
    if limit:
        return random.Random(seed).sample(members, min(limit, len(members)))
    return members


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("set", metavar="SET", help="the set whose cards were written into the instance")
    parser.add_argument("server", metavar="SERVER", help="the MCP server the instance answers on")
    parser.add_argument("instance", metavar="INSTANCE_ID", help="the same instance by its id, which the marks are written under")
    parser.add_argument("--limit", type=int, default=0, help="observe this many cards, chosen at random")
    parser.add_argument("--cards", default=None, help="observe exactly these, as source/number, comma separated")
    parser.add_argument("--seed", type=int, default=1, help="fixes which cards --limit chooses")
    parser.add_argument("--model", default="sonnet", help="the model that observes (default: sonnet)")
    parser.add_argument("--parallel", type=int, default=4, help="sessions at once (default: 4)")
    parser.add_argument("--db", default=None, help="database to write the marks to (default: MONGO_DB)")
    args = parser.parse_args(argv)

    try:
        with database(args.db) as db:
            try:
                members = sets.members(db, args.set)
            except KeyError as error:
                sys.exit(error.args[0])
            wanted = chosen(members, args.cards, args.limit, args.seed)

            print("%d observations of %s, model %s, memory %s (%s)" % (
                len(wanted), args.set, args.model, args.server, args.instance), flush=True)
            done, failed = 0, []
            with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                running = {pool.submit(observe, s, e, args.server, args.model): (s, e) for s, e in wanted}
                for future in running:
                    source, external_id = running[future]
                    try:
                        record, elapsed = future.result()
                    except Exception as error:  # a session that timed out or would not start
                        record, elapsed = {"error": str(error)}, 0
                    done += 1
                    marks = record.get("marks")
                    if marks:
                        try:
                            observations.record(
                                db, args.instance, args.set, source, external_id, marks,
                                model=args.model, cost_usd=record.get("cost_usd"),
                                seconds=round(elapsed))
                        except (WriteError, ValueError) as error:
                            record["error"] = "the marks were refused: %s" % error
                            record["reply"] = json.dumps(marks, ensure_ascii=False)
                            marks = None
                    print("%s %2d/%d %-30s %-8s %-8s $%.3f  %ds" % (
                        datetime.now().strftime("%H:%M:%S"), done, len(wanted), source, external_id,
                        "/".join(str(marks[axis]["score"]) for axis in ("schedule", "event", "place"))
                        if marks else "FAILED",
                        record.get("cost_usd") or 0.0, round(elapsed)), flush=True)
                    if not marks:
                        failed.append((source, external_id))
                        print("     %s" % record.get("error", ""), flush=True)
                        if record.get("reply"):
                            print("     %s" % record["reply"].replace("\n", " ")[-500:], flush=True)
            print("done: %d observed, %d failed" % (done - len(failed), len(failed)), flush=True)
            if failed:
                print("failed: %s" % ", ".join("%s/%s" % key for key in failed), flush=True)
    except PyMongoError as error:
        sys.exit("database error: %s" % error)


if __name__ == "__main__":
    main()
