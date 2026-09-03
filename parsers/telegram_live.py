"""Read Telegram channels as they publish, and keep the posts as cards.

Which channels are read is a question for the database, not for this file: the
`sources` collection holds one document per channel, and adding a channel is a
row rather than a deployment. Every source carries a cursor — the id of the
last post already stored — and a pass asks the channel for what came after it.

Freshness is not what this is for; not losing a post is. So the parser asks
every so often instead of listening for updates, and the cursor moves only
once a card is in the database. A pass that fails halfway, a restart, a deploy
in the middle of a channel all end the same way: the cursor stands where the
last stored card left it, and the next pass carries on from there. A post read
twice is written twice over the same card and costs nothing.

On a server, reading every source there is:

    python -m parsers.telegram_live [--db NAME] [--interval SECONDS] [--once]

While developing, reading one channel named on the command line — the database
is not opened, no cursor moves, and the cards go to the terminal or to files:

    python -m parsers.telegram_live --channel a_channel [--limit N] [--out DIR]

Once, before any of that, to sign the account in and leave a session behind:

    python -m parsers.telegram_live --login

Settings come from the repository's `.env` — see `envfile`:

    TELEGRAM_API_ID      the application id from my.telegram.org
    TELEGRAM_API_HASH    the hash beside it
    TELEGRAM_SESSION     where the signed-in session is kept
"""
import argparse
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

if __package__ in (None, ""):  # run by path rather than with -m: put the repo on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon.errors import FloodWaitError, RPCError
from telethon.sync import TelegramClient
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

import envfile
from parsers.card import Card
from parsers.sinks import JsonFileSink, PrintSink
from parsers.sinks.mongo import MongoSink
from storage import sources
from storage.mongo import database

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SESSION = os.path.join(REPO, ".telegram.session")
DEFAULT_INTERVAL = 600
DEFAULT_LIMIT = 20
CHANNEL = "t.me/"


def report(line):
    """One line of what the run is doing, stamped and flushed for the journal."""
    print("%s %s" % (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), line), flush=True)


def credentials():
    """The application the parser signs in as, and where its session is kept."""
    values = envfile.by_prefix("TELEGRAM_")
    hint = "get one at my.telegram.org and put it in .env"
    api_id = envfile.require(values, "TELEGRAM_API_ID", hint)
    api_hash = envfile.require(values, "TELEGRAM_API_HASH", hint)
    return int(api_id), api_hash, values.get("TELEGRAM_SESSION") or DEFAULT_SESSION


def channel_of(source):
    """The channel a source name points at: `t.me/a_channel` -> `a_channel`."""
    name = source[len(CHANNEL):] if source.startswith(CHANNEL) else ""
    if not name or "/" in name:
        raise ValueError("not a Telegram channel: %s" % source)
    return name


def source_of(channel):
    """The source name a channel's cards carry: `a_channel` -> `t.me/a_channel`."""
    return CHANNEL + channel.strip().lstrip("@")


def post_text(message):
    """Visible text of a post, empty for anything that has none.

    A service message — a pin, a title change — carries an action instead of
    text, and the other frames of an album carry a photo and nothing else. Both
    come out empty here, and neither becomes a card.
    """
    if getattr(message, "action", None) is not None:
        return ""
    return (getattr(message, "message", None) or "").strip()


def post_links(message):
    """URLs the post carried, in order, without repeats.

    A link hidden behind anchor text keeps its URL in the entity; a bare one is
    the text it covers. Entity offsets count UTF-16 code units rather than
    characters, so the text is measured in those before a bare URL is cut out.
    """
    links = []
    units = (getattr(message, "message", None) or "").encode("utf-16-le")
    for entity in getattr(message, "entities", None) or ():
        if isinstance(entity, MessageEntityTextUrl):
            url = entity.url
        elif isinstance(entity, MessageEntityUrl):
            url = units[entity.offset * 2:(entity.offset + entity.length) * 2].decode("utf-16-le")
        else:
            continue
        if url and url not in links:
            links.append(url)
    return links


def card_of(message, source):
    """A card from one post, or None when the post has nothing to put on one."""
    text = post_text(message)
    if not text:
        return None
    return Card(id=message.id, source=source, date=message.date, text=text,
                links=post_links(message))


@contextmanager
def connected():
    """A signed-in client, disconnected when the block ends."""
    api_id, api_hash, session = credentials()
    client = TelegramClient(session, api_id, api_hash)
    client.connect()
    try:
        if not client.is_user_authorized():
            raise SystemExit(
                "no signed-in session at %s: run `python -m parsers.telegram_live --login`"
                % session)
        yield client
    finally:
        client.disconnect()


def login():
    """Sign the account in and leave a session file behind. Asks for a code."""
    api_id, api_hash, session = credentials()
    with TelegramClient(session, api_id, api_hash) as client:
        account = client.get_me()
        print("signed in as %s, session kept in %s" % (account.username or account.id, session))


def messages_after(client, source, cursor, start_at):
    """Posts of a source that come after where it was left, oldest first.

    With a cursor the channel is asked for everything past that post. Without
    one — a source just added — it is asked for what it published from
    `start_at` on, so a new channel brings its future and not its archive.
    """
    channel = channel_of(source)
    if cursor:
        return client.iter_messages(channel, min_id=int(cursor), reverse=True)
    return client.iter_messages(channel, offset_date=start_at, reverse=True)


def read_source(client, db, sink, source):
    """Take everything new from one source. Returns posts seen and cards added."""
    name = source["source"]
    seen = added = 0
    for message in messages_after(client, name, source.get("lastMessageId"), source["startAt"]):
        try:
            card = card_of(message, name)
        except ValueError as error:
            # One post nothing can be made of must not wedge the channel behind
            # it: it is reported, the cursor passes over it, and the rest of the
            # source is read.
            report("%s post %s did not make a card: %s" % (name, message.id, error))
            card = None
        if card is not None and sink.send(card):
            added += 1
        seen += 1
        # After the card is stored, never before: a stop here costs a post read
        # twice, a stop the other way round costs a post nobody ever reads.
        sources.advance(db, name, message.id)
    if not seen:
        sources.polled(db, name)
    return seen, added


def pass_over(client, db, sink):
    """One pass over every source being read. A source that fails is reported."""
    for source in sources.active(db):
        name = source["source"]
        try:
            seen, added = read_source(client, db, sink, source)
        except FloodWaitError as error:
            report("%s asked to wait %d seconds — left for the next pass" % (name, error.seconds))
        except (RPCError, OSError, ValueError) as error:
            # A channel that is gone, renamed, closed, or briefly unreachable
            # is one channel's problem: the pass carries on with the rest, and
            # the cursor of this one is where its last stored card left it.
            report("%s could not be read: %s" % (name, error))
        else:
            if seen:
                report("%s %d posts, %d new cards" % (name, seen, added))


def watch(db, interval, once):
    """Read every source, again and again, until the process is stopped."""
    sink = MongoSink(db)
    with connected() as client:
        while True:
            pass_over(client, db, sink)
            if once:
                break
            time.sleep(interval)
    return sink


def show(channels, out=None, limit=DEFAULT_LIMIT):
    """Read channels named on the command line, touching no database."""
    sink = JsonFileSink(out) if out else PrintSink()
    with connected() as client, sink:
        for channel in channels:
            source = source_of(channel)
            for message in client.iter_messages(channel, limit=limit):
                card = card_of(message, source)
                if card is not None:
                    sink.send(card)
    return sink


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--login", action="store_true",
                        help="sign the account in and write the session file, then stop")
    parser.add_argument("--channel", action="append", metavar="NAME", default=None,
                        help="read this channel instead of the sources in the database; repeatable")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="how many posts to take per channel with --channel (default: %d)" % DEFAULT_LIMIT)
    parser.add_argument("--out", default=None,
                        help="write the cards of --channel as files under this directory")
    parser.add_argument("--db", default=None, help="database to write to (default: MONGO_DB)")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="seconds between passes (default: %d)" % DEFAULT_INTERVAL)
    parser.add_argument("--once", action="store_true",
                        help="make a single pass over the sources and stop")
    args = parser.parse_args(argv)

    if args.login:
        login()
        return

    if args.channel:
        sink = show(args.channel, args.out, args.limit)
        print("%d cards%s" % (sink.count, " written to " + args.out if args.out else ""))
        return

    try:
        with database(args.db) as db:
            report("reading %s every %d seconds" % (db.name, args.interval))
            sink = watch(db, args.interval, args.once)
            report("stopped — %d cards added, %d already stored" % (sink.added, sink.refreshed))
    except KeyboardInterrupt:
        report("stopped")


if __name__ == "__main__":
    main()
