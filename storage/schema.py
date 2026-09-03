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

# Where a rule stands. `draft` was proposed and not yet judged; `active` passed
# the gate and the filter is given it; `rejected` failed the gate and is kept so
# that it is not proposed again.
RULE_STATUSES = ("draft", "active", "rejected")

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

    # A rule the filter is given alongside the cards. Each is bound to one
    # reason from the closed list and is of one form — if the text says
    # such-and-such, do not give this reason: where the text does, the filter
    # lifts the reason. A rule can only take a reason away, never
    # add one, so two rules cannot contradict each other. `name` is how a
    # verdict refers to it, `cards` are the cards it was drawn from, `gate`
    # the numbers it was judged on.
    "rules": {
        "indexes": [
            {"keys": [("name", 1)], "name": "name", "unique": True},
            {"keys": [("status", 1)], "name": "status", "unique": False},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["name", "reason", "text", "status", "cards", "proposedAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "name": {"bsonType": "string", "pattern": r"^[a-z0-9]+(?:-[a-z0-9]+)*$"},
                    # The reason the rule withholds. `unknown` is not a reason a rule corrects.
                    "reason": {"enum": sorted(set(REASONS) - {"unknown"})},
                    # When the reason is lifted: "if the text says …, do not give <reason>".
                    "text": {"bsonType": "string", "minLength": 1},
                    "status": {"enum": list(RULE_STATUSES)},
                    "cards": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "object",
                            "required": ["source", "externalId"],
                            "additionalProperties": False,
                            "properties": {
                                "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                                "externalId": {"bsonType": "string"},
                            },
                        },
                    },
                    "proposedAt": {"bsonType": "date"},
                    # Where the rule came from: the run whose disagreements it was drawn from, or a note.
                    "proposedFrom": {"bsonType": "string"},
                    "decidedAt": {"bsonType": "date"},
                    # What the gate saw: the candidate run against the base run over `of`
                    # answered cards — agreement before and after on the whole set, and on
                    # the `fired` cards the rule described, how many it fixed and broke.
                    "gate": {
                        "bsonType": "object",
                        "required": ["run", "base", "of", "agreeBefore", "agreeAfter", "fired", "fixed", "broken"],
                        "additionalProperties": False,
                        "properties": {
                            "run": {"bsonType": "string", "minLength": 1},
                            "base": {"bsonType": "string", "minLength": 1},
                            "of": {"bsonType": "int"},
                            "agreeBefore": {"bsonType": "int"},
                            "agreeAfter": {"bsonType": "int"},
                            "fired": {"bsonType": "int"},
                            "fixed": {"bsonType": "int"},
                            "broken": {"bsonType": "int"},
                            "brokenOnAccept": {"bsonType": "int"},
                        },
                    },
                },
            },
        },
    },

    # One run of the judge: which rules it was given and which model judged,
    # so that its verdicts can be read back knowing what produced them.
    "runs": {
        "indexes": [
            {"keys": [("run", 1)], "name": "run", "unique": True},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["run", "model", "rules", "startedAt", "lastAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "run": {"bsonType": "string", "minLength": 1},
                    "model": {"bsonType": "string", "minLength": 1},
                    # The rules the filter was given, by name; empty for a run without rules.
                    "rules": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "startedAt": {"bsonType": "date"},
                    "lastAt": {"bsonType": "date"},
                },
            },
        },
    },

    # A source the online parser reads, and where it got to in it. Adding a
    # document here is how a channel starts being read; there is nothing to
    # deploy. `lastMessageId` is the last post taken from the source, and the
    # parser that owns the source is what knows how to ask for what came
    # after it. A source that has no cursor yet is read from `startAt` on —
    # history is loaded from an export, not fetched back through the source.
    "sources": {
        "indexes": [
            {"keys": [("source", 1)], "name": "source", "unique": True},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["source", "enabled", "startAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                    "enabled": {"bsonType": "bool"},
                    "startAt": {"bsonType": "date"},
                    "lastMessageId": {"bsonType": ["int", "long"]},
                    "lastPolledAt": {"bsonType": "date"},
                },
            },
        },
    },
}
