"""Read a Telegram channel export and turn its posts into cards.

An export is a directory Telegram Desktop wrote: one `result.json` holding
every message, plus the media it downloaded. Only `result.json` is read here —
the media is left where it is.

Usage, from the repository root:

    python -m parsers.telegram_history [PATH ...] [--out DIR] [--dry-run]

or by path, from anywhere:

    python <repo>/parsers/telegram_history.py [PATH ...]

PATH is an export directory, or a directory holding several of them. It and
`--out` default to the working material of the repository this file lives in,
whatever the current directory is.

What is dropped, and why:

- anything that is not a plain `message` — pinned-message notices and the
  `unsupported` placeholders Telegram writes for media it cannot export;
- messages whose text is empty. Those are the other frames of an album: the
  caption rides on one message of it and its siblings carry only a photo, so
  there is nothing to put on a card.
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.card import Card
from parsers.sinks import CountingSink, JsonFileSink

EXPORT_FILE = "result.json"
# The exports and the cards live with the repository, not with whoever calls this.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(REPO, "untracked")
DEFAULT_OUT = os.path.join(REPO, "untracked", "cards")


def source_name(export_dir):
    """Source name from the export directory: `t.me kudagospb` -> `t.me/kudagospb`."""
    parts = os.path.basename(os.path.normpath(export_dir)).split()
    return "/".join(parts) if parts else "unknown"


def post_text(message):
    """Visible text of a message, links reduced to the words they were hung on."""
    entities = message.get("text_entities")
    if entities:
        return "".join(entity.get("text", "") for entity in entities)
    text = message.get("text")
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        return "".join(part if isinstance(part, str) else part.get("text", "") for part in text)
    return ""


def post_links(message):
    """URLs the message carried, in order, without repeats.

    A `text_link` hides its URL behind the anchor text and keeps it in `href`;
    a bare `link` is the URL itself.
    """
    links = []
    for entity in message.get("text_entities") or []:
        kind = entity.get("type")
        url = entity.get("href") if kind == "text_link" else entity.get("text") if kind == "link" else None
        if url and url not in links:
            links.append(url)
    return links


def read_export(export_dir, tally=None):
    """Yield a Card per usable post in one export, counting what it passes over."""
    tally = Counter() if tally is None else tally
    source = source_name(export_dir)
    with open(os.path.join(export_dir, EXPORT_FILE), encoding="utf-8") as fh:
        export = json.load(fh)

    for message in export.get("messages") or []:
        tally["messages"] += 1
        if message.get("type") != "message":
            tally["not a message"] += 1
            continue
        text = post_text(message).strip()
        if not text:
            tally["without text"] += 1
            continue
        yield Card(
            id=message["id"],
            source=source,
            date=datetime.fromisoformat(message["date"]),
            text=text,
            links=post_links(message),
        )


def find_exports(path):
    """Every export directory at `path`, or one level below it."""
    if os.path.isfile(os.path.join(path, EXPORT_FILE)):
        return [path]
    found = []
    for entry in sorted(os.listdir(path)):
        candidate = os.path.join(path, entry)
        if os.path.isfile(os.path.join(candidate, EXPORT_FILE)):
            found.append(candidate)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", default=[DEFAULT_PATH],
                        help="export directory, or a directory of them (default: untracked/ of the repository)")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="where cards are written (default: untracked/cards of the repository)")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the exports and report, without writing anything")
    args = parser.parse_args(argv)

    exports = []
    for path in args.paths or [DEFAULT_PATH]:
        if not os.path.isdir(path):
            sys.exit("not a directory: " + path)
        exports.extend(find_exports(path))
    if not exports:
        sys.exit("no export found: looked for %s under %s" % (EXPORT_FILE, ", ".join(args.paths)))

    sink = CountingSink() if args.dry_run else JsonFileSink(args.out)
    with sink:
        for export_dir in exports:
            tally = Counter()
            sent = 0
            for card in read_export(export_dir, tally):
                sink.send(card)
                sent += 1
            print("%-24s %5d cards  (%d messages, %d without text, %d not a message)" % (
                source_name(export_dir), sent, tally["messages"],
                tally["without text"], tally["not a message"]))

    if args.dry_run:
        print("%d cards read, nothing written" % sink.count)
    else:
        print("%d cards written to %s" % (sink.count, args.out))


if __name__ == "__main__":
    main()
