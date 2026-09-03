# storage

Posts live in MongoDB: the cards themselves, the answer a person gave about a card, and
the sources being read. This module owns that database — what its collections hold, the
rules the database enforces, and the commands that create and fill them.

## What is kept

| | |
| --- | --- |
| `cards` | one post as it stood in its source, in the shape a parser produces |
| `answers` | the right answer about one card: was it an event, and if not, why |
| `sources` | a source being read, and how far into it the reading got |

Not every database holds all three. The evaluation set keeps cards and the answers given
about them; the database that collects posts keeps cards and the sources they come from.
Which collections a database has is said when it is created, and the schema is the same
either way.

A card is addressed by `(source, externalId)`, and an answer refers to the same pair.
Cards here are a copy taken once: an answer was given about a particular text, so
re-reading the source must not change it underneath the answer.

An answer is `accept` — whether the card is an event worth keeping — and `reasons`,
which only a refusal carries:

| | |
| --- | --- |
| `missing_event` | no event in the text: news, a photograph, a thought, the channel about itself |
| `missing_time` | an event, but no date or time |
| `missing_place` | an event, but no venue, or none a reader could find |
| `multiple_events` | a roundup: several events, none of them the subject of the card |
| `not_visit_worthy` | something happening in the city rather than an event to attend: a closed bridge, a jam, roadworks |
| `unknown` | none of the listed reasons fits, or the card cannot be read with confidence |

The list is closed: a reason outside it cannot be stored. The same words have to mean
the same thing to everyone who writes here, so a new reason is a change to
`schema.py` — and to whatever has already been answered under the old list.

A source is a name and a place in it: `startAt`, the moment to read from before anything
has been read, and `lastMessageId`, the last post already stored. The cursor moves only
after a card is in `cards`, so a reader that stops between the two takes one post twice —
which the upsert absorbs — rather than stepping over it. A source can be switched off with
`enabled` without being forgotten.

Dates are stored as they arrive on a card: UTC, and never without a zone.

Mongo asks for no schema and would take a document of any shape, which is how a
misspelled field becomes a second, silent one. Every collection therefore carries a
validator, and a document that does not fit is refused at write time.

## Running it

Credentials come from `.env` at the repository root, which git ignores. Copy
`.env.example` to `.env` and fill in `MONGO_URI` and `MONGO_DB`. Both can also come
from the environment, which wins over the file.

Install what it needs, from the repository root:

```
pip install -r requirements.txt
```

Create the collections, their validators and their indexes:

```
python -m storage.setup [COLLECTION ...] [--db NAME]
```

Naming collections brings up those and leaves the rest alone; naming none brings up
everything in the schema. It is idempotent — run it on an empty database to start one, and
again after a change to `schema.py` to apply it.

Put cards that already exist as JSON files into `cards`:

```
python -m storage.load_cards [PATH ...] [--db NAME] [--dry-run]
```

`PATH` is a card file or a directory searched at any depth. Loading the same files
twice leaves one copy of each: a card is upserted by `(source, externalId)`, its post
refreshed and everything else left alone, so an answer already given survives it.

Add a source to read:

```
python -m storage.add_source SOURCE [--db NAME] [--since WHEN]
```

Reading starts where the cards already stored for that source end, so loading an export
first and adding the source after leaves no gap between the two. A source with no cards
starts from now, and `--since` overrides both. Adding the same source twice reports what is
already there and changes nothing.

## Files

| | |
| --- | --- |
| `schema.py` | what each collection holds and the rules the database enforces |
| `mongo.py` | credentials and the connection they open |
| `cards.py` | writing cards and asking what is already stored |
| `answers.py` | recording the answer about a card |
| `sources.py` | the sources being read, and where the reading got to |
| `setup.py` | creates the collections and brings them to the current schema |
| `load_cards.py` | reads card files and puts them in `cards` |
| `add_source.py` | adds a source to read |
