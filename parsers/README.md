# Parsers

A parser reads one source of posts and produces a card per post — the post as it stands,
not what it means. Each source gets its own parser; they all produce the same card.

Three parts, kept apart on purpose:

| | |
| --- | --- |
| `card.py` | the card: the contract every parser produces and every sink accepts |
| `<parser>.py` | reads one source and builds cards from it |
| `sinks/` | takes the cards a parser built and puts them somewhere |

A parser never writes anything itself — it hands each card to a sink. Today the sink that
keeps cards writes JSON files; a database or a queue fits behind the same `send`.

## The card

```json
{
  "id": "1234",
  "source": "t.me/example_channel",
  "date": "2026-05-01T15:03:01+00:00",
  "text": "Open call for muralists, applications close on 12 May. Details at the link.",
  "links": ["https://example.org/open-call"]
}
```

`text` is what a reader sees, so a link contributes the words it was hung on and its URL
goes to `links` instead. `id` is the post's id in its own source: it makes a card
addressable and a re-run idempotent. `date` is UTC, and a card refuses a date with no
time zone — two parsers reading the same post have to agree about when it happened.

`JsonFileSink` writes one file per card and derives the path from the card:

```
<out>/<source>/<YYYY-MM-DD>/<post-id>.json
```

## telegram_history

Posts from a Telegram channel, taken from an export made by Telegram Desktop. The export
is a directory; the parser reads the `result.json` in it and leaves the downloaded media
alone. Service messages and posts without text are skipped, and the run reports how many
of each it dropped.

From the repository root:

```
python -m parsers.telegram_history [PATH ...] [--out DIR] [--source NAME] [--dry-run]
```

or by path, from anywhere — `-m` only finds the package when the root is the working
directory:

```
python <repo>/parsers/telegram_history.py [PATH ...]
```

- `PATH` — an export directory, or a directory holding several of them.
- `--out DIR` — where cards are written.
- `--source NAME` — the source the cards carry, for one export at a time. Otherwise the
  name comes from the export directory: `t.me kudagospb` becomes `t.me/kudagospb`, and
  the directories Telegram Desktop names after the day it wrote them say nothing useful.
- `--dry-run` — read the exports and report, without writing anything.

`PATH` and `--out` default to the working material of the repository, wherever the
command is run from. Python 3 and the standard library — nothing to install.
