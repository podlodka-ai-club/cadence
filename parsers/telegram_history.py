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

The source a card carries is read from the name of the export directory —
`t.me kudagospb` becomes `t.me/kudagospb`. Telegram Desktop names its exports
after the day it made them, so `--source` says the name outright when the
directory does not.

What is dropped, and why:

- anything that is not a plain `message` — pinned-message notices and the
  `unsupported` placeholders Telegram writes for media it cannot export;
- messages whose text is empty. Those are the other frames of an album: the
  caption rides on one message of it and its siblings carry only a photo, so
  there is nothing to put on a card.

The time on a card is UTC, read from `date_unixtime`. The `date` beside it is
the local time of whoever made the export and says nothing about the post.
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.card import SOURCE_NAME, Card
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


def post_date(message):
    """When the post was made, in UTC.

    The export states the time twice: `date`, in the local time of the machine
    that made the export, and `date_unixtime`, the moment itself. Only the
    second one means the same thing to a second reader, so an export that
    lacks it is refused rather than read hours out.
    """
    unixtime = message.get("date_unixtime")
    if unixtime is None:
        raise ValueError(
            "message %s has no date_unixtime: this export is too old to read" % message.get("id"))
    return datetime.fromtimestamp(int(unixtime), timezone.utc)


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


def read_export(export_dir, tally=None, source=None):
    """Yield a Card per usable post in one export, counting what it passes over."""
    tally = Counter() if tally is None else tally
    source = source or source_name(export_dir)
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
            date=post_date(message),
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
    parser.add_argument("--source", default=None, metavar="NAME",
                        help="the source the cards carry, when the directory is not named after it")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the exports and report, without writing anything")
    args = parser.parse_args(argv)

    if args.source and not SOURCE_NAME.match(args.source):
        sys.exit("not a usable source name: %r" % args.source)

    exports = []
    for path in args.paths or [DEFAULT_PATH]:
        if not os.path.isdir(path):
            sys.exit("not a directory: " + path)
        exports.extend(find_exports(path))
    if not exports:
        sys.exit("no export found: looked for %s under %s" % (EXPORT_FILE, ", ".join(args.paths)))
    if args.source and len(exports) > 1:
        sys.exit("--source names one export, but %d were found under %s" % (
            len(exports), ", ".join(args.paths)))

    sink = CountingSink() if args.dry_run else JsonFileSink(args.out)
    with sink:
        for export_dir in exports:
            tally = Counter()
            sent = 0
            for card in read_export(export_dir, tally, args.source):
                sink.send(card)
                sent += 1
            print("%-28s %5d cards  (%d messages, %d without text, %d not a message)" % (
                args.source or source_name(export_dir), sent, tally["messages"],
                tally["without text"], tally["not a message"]))

    if args.dry_run:
        print("%d cards read, nothing written" % sink.count)
    else:
        print("%d cards written to %s" % (sink.count, args.out))


if __name__ == "__main__":
    main()
