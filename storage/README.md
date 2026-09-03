# storage

The evaluation set lives in MongoDB: the cards it is made of, and the answer a person
gave about each of them. This module owns that database — what its collections hold,
the rules the database enforces, and the commands that create and fill them.

## What is kept

| | |
| --- | --- |
| `cards` | one post as it stood in its source, in the shape a parser produces |
| `answers` | the right answer about one card: was it an event, and if not, why |

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
python -m storage.setup [--db NAME]
```

It is idempotent — run it on an empty database to start one, and again after a change
to `schema.py` to apply it.

Put cards that already exist as JSON files into `cards`:

```
python -m storage.load_cards [PATH ...] [--db NAME] [--dry-run]
```

`PATH` is a card file or a directory searched at any depth. Loading the same files
twice leaves one copy of each: a card is upserted by `(source, externalId)`, its post
refreshed and everything else left alone, so an answer already given survives it.

## Files

| | |
| --- | --- |
| `schema.py` | what each collection holds and the rules the database enforces |
| `mongo.py` | credentials and the connection they open |
| `setup.py` | creates the collections and brings them to the current schema |
| `load_cards.py` | reads card files and puts them in `cards` |
