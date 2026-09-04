"""What each collection holds, and the rules the database enforces on it.

Mongo asks for no schema: a collection appears with the first document and
takes whatever shape it is handed. That is how a misspelled field becomes a
second, silent schema — nothing fails, the document is simply never found
again. So every collection here carries a validator, and `storage.setup` puts
it on the database. A document that does not fit is refused at write time.

This file is the one place the shapes are written down. `setup` applies them;
everything that writes reads them from here.
"""

# Why a card was refused. A closed list on purpose: the same words have to
# mean the same thing to whoever answers by hand, to the filter, and to
# whatever compares the two. A reason outside this list cannot be stored.
REASONS = {
    "missing_event": "no event in the text: news, a photograph, a thought, the channel about itself",
    "missing_time": "an event, but no date or time",
    "missing_place": "an event, but no venue, or none a reader could find",
    "multiple_events": "a roundup: several events, none of them the subject of the card",
    "not_visit_worthy": "something happening in the city rather than an event to attend: a closed bridge, a jam, roadworks",
    "unknown": "none of the listed reasons fits, or the card cannot be read with confidence",
}

# A source name is a path-safe name of where the post came from: `t.me/a_channel`.
# Segments of word characters joined by `/`, and no `.` or `..` segment that
# could walk out of a directory built from it — the same rule `parsers.card`
# applies before a card is ever built.
SOURCE_SEGMENT = r"(?!\.{1,2}(?:/|$))[\w.-]+"
SOURCE_PATTERN = r"^%s(?:/%s)*$" % (SOURCE_SEGMENT, SOURCE_SEGMENT)

COLLECTIONS = {
    # One post as it stood in its source — the shape a parser produces, and
    # nothing else. A card here is a copy taken once: it is what the answers
    # were given about, so re-reading the source must not change it underneath
    # them.
    "cards": {
        "indexes": [
            {"keys": [("source", 1), ("externalId", 1)], "name": "source_externalId", "unique": True},
            {"keys": [("date", 1)], "name": "date", "unique": False},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["source", "externalId", "date", "text", "links"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                    "externalId": {"bsonType": "string"},
                    "date": {"bsonType": "date"},
                    "text": {"bsonType": "string", "minLength": 1},
                    "links": {"bsonType": "array", "items": {"bsonType": "string"}},
                },
            },
        },
    },
    # The right answer about one card, given by a person. `accept` is whether
    # the card is an event worth keeping; `reasons` says why not, and only a
    # refusal has any.
    "answers": {
        "indexes": [
            {"keys": [("source", 1), ("externalId", 1)], "name": "source_externalId", "unique": True},
        ],
        "validator": {
            "$and": [
                {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["source", "externalId", "accept", "reasons", "answeredAt"],
                        "additionalProperties": False,
                        "properties": {
                            "_id": {"bsonType": "objectId"},
                            "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                            "externalId": {"bsonType": "string"},
                            "accept": {"bsonType": "bool"},
                            "reasons": {
                                "bsonType": "array",
                                "uniqueItems": True,
                                "items": {"enum": sorted(REASONS)},
                            },
                            "answeredAt": {"bsonType": "date"},
                        },
                    },
                },
                # An accepted card has nothing to explain; a refused one always says why.
                {
                    "$or": [
                        {"accept": True, "reasons": {"$size": 0}},
                        {"accept": False, "reasons": {"$not": {"$size": 0}}},
                    ],
                },
            ],
        },
    },

    # What the filter said about one card in one run. `run` names the run:
    # `live` is the filter as it stands in production, one verdict per card,
    # rewritten each time the card is judged; any other name is an evaluation
    # run, kept whole so two of them can be compared. The eval set itself is
    # `answers` — a verdict never becomes an answer without a person.
    "verdicts": {
        "indexes": [
            {"keys": [("run", 1), ("source", 1), ("externalId", 1)], "name": "run_source_externalId", "unique": True},
            {"keys": [("source", 1), ("externalId", 1)], "name": "source_externalId", "unique": False},
        ],
        "validator": {
            "$and": [
                {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["run", "source", "externalId", "accept", "reasons", "rules", "model", "judgedAt"],
                        "additionalProperties": False,
                        "properties": {
                            "_id": {"bsonType": "objectId"},
                            "run": {"bsonType": "string", "minLength": 1},
                            "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                            "externalId": {"bsonType": "string"},
                            "accept": {"bsonType": "bool"},
                            "reasons": {
                                "bsonType": "array",
                                "uniqueItems": True,
                                "items": {"enum": sorted(REASONS)},
                            },
                            # What the filter could not settle; comes only with `unknown`.
                            "note": {"bsonType": "string"},
                            # The rules the filter applied to reach the verdict, by their ids.
                            "rules": {"bsonType": "array", "items": {"bsonType": "string"}},
                            # The model that judged: a verdict is only comparable to one from the same.
                            "model": {"bsonType": "string", "minLength": 1},
                            "judgedAt": {"bsonType": "date"},
                        },
                    },
                },
                # The same rule as for an answer: an accepted card has nothing to explain.
                {
                    "$or": [
                        {"accept": True, "reasons": {"$size": 0}},
                        {"accept": False, "reasons": {"$not": {"$size": 0}}},
                    ],
                },
            ],
        },
    },
}
