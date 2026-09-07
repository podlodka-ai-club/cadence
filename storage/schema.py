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

# Who a rule is addressed to. A `filter` rule is given to the filter alongside a
# card and withholds one refusal reason; a `memory` rule is given to whatever
# writes a post into memory and says how to read one. The two are drawn from
# different evidence and judged by different numbers, and never mix.
RULE_TARGETS = ("filter", "memory")

# The three parts of a post an observation marks, each on its own.
OBSERVATION_AXES = ("schedule", "event", "place")

# What a mark below 5 is blamed on. The observer hands out these labels and says
# `other` where none of them fits — which is how the list learns it is short.
# The vocabulary is written down here for whatever counts labels; unlike the
# refusal reasons it is not enforced at write time, because an observation has
# already been paid for by the memory it questioned and a label outside the list
# is a finding rather than a reason to refuse it.
OBSERVATION_LABELS = {
    "schedule": ("no-occurrences", "mode-collapsed", "doors-time", "end-missing",
                 "time-lost", "wrong-date", "occurrence-duplicate"),
    "event": ("duplicate", "title-generic", "facts-lost", "not-found", "unlinked"),
    "place": ("duplicate", "name-is-address", "address-missing", "two-places-in-one",
              "not-found", "unlinked"),
}

# One mark: what it is, what it is blamed on, and why it was given. A 5 carries
# no label and anything less carries at least one, but that is the observer's
# business rather than the database's — see OBSERVATION_LABELS.
MARK = {
    "bsonType": "object",
    "required": ["score", "labels", "why"],
    "additionalProperties": False,
    "properties": {
        "score": {"enum": [0, 3, 5]},
        "labels": {"bsonType": "array", "uniqueItems": True, "items": {"bsonType": "string"}},
        "why": {"bsonType": "string", "minLength": 1},
    },
}

# A name that reads the same to a person and to a path: lowercase words joined by dashes.
NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

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
            {"keys": [("target", 1), ("status", 1)], "name": "target_status", "unique": False},
        ],
        "validator": {
          "$and": [
            {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["name", "target", "text", "status", "cards", "proposedAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "name": {"bsonType": "string", "pattern": NAME_PATTERN},
                    # Who the rule is addressed to: the filter, or whatever writes into memory.
                    "target": {"enum": list(RULE_TARGETS)},
                    # The reason the rule withholds — a filter rule only, and never `unknown`.
                    "reason": {"enum": sorted(set(REASONS) - {"unknown"})},
                    # A filter rule: when the reason is lifted, "if the text says …, do not
                    # give <reason>". A memory rule: how to read a post of a certain kind.
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
                    # What the gate saw. A filter rule is judged on runs: the candidate
                    # run against the base run over `of` answered cards — agreement before
                    # and after on the whole set, and on the `fired` cards the rule
                    # described, how many it fixed and broke. A memory rule is judged on
                    # observations: the same cards observed in the instance written
                    # `before` the rule and in the one written `after` it, their marks
                    # summed, and how many cards rose and how many lost an axis.
                    "gate": {
                        "oneOf": [
                            {
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
                            {
                                "bsonType": "object",
                                "required": ["before", "after", "of", "scoreBefore", "scoreAfter", "fixed", "broken"],
                                "additionalProperties": False,
                                "properties": {
                                    "before": {"bsonType": "string", "minLength": 1},
                                    "after": {"bsonType": "string", "minLength": 1},
                                    "of": {"bsonType": "int"},
                                    "scoreBefore": {"bsonType": "int"},
                                    "scoreAfter": {"bsonType": "int"},
                                    "fixed": {"bsonType": "int"},
                                    "broken": {"bsonType": "int"},
                                },
                            },
                        ],
                    },
                },
            },
            },
            # Only a filter rule is bound to a refusal reason; a memory rule
            # corrects how a post is read, and there is no reason to name.
            {
                "$or": [
                    {"target": "filter", "reason": {"$exists": True}},
                    {"target": "memory", "reason": {"$exists": False}},
                ],
            },
          ],
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

    # A named set of cards to judge, fixed once and never edited: a run over a
    # set is comparable to any other run over it, which it would not be if the
    # cards underneath had moved. Changing the choice means writing another
    # set, not touching this one. `cards` keeps the order the cards were
    # chosen in, and `why` on each says what it is there for — a defect it
    # once produced, or the control it provides.
    "sets": {
        "indexes": [
            {"keys": [("name", 1)], "name": "name", "unique": True},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["name", "cards", "createdAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    "name": {"bsonType": "string", "pattern": NAME_PATTERN},
                    # What the set is for, in a sentence.
                    "note": {"bsonType": "string"},
                    "cards": {
                        "bsonType": "array",
                        "minItems": 1,
                        "items": {
                            "bsonType": "object",
                            "required": ["source", "externalId"],
                            "additionalProperties": False,
                            "properties": {
                                "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                                "externalId": {"bsonType": "string"},
                                "why": {"bsonType": "array", "items": {"bsonType": "string"}},
                            },
                        },
                    },
                    "createdAt": {"bsonType": "date"},
                },
            },
        },
    },

    # One observation: what one post left in one memory, as an observer saw it.
    # Three marks — the times the event is held, the event itself, the venue —
    # each with what it is blamed on and why it was given. There is no right
    # answer written by a person here: the observer holds the post against what
    # memory returned and says how far apart they are, which is what makes an
    # observation cheap enough to have many of.
    #
    # `instance` is the memory that was questioned; the same post observed in
    # two instances is two records, and that is the whole point — a rule is
    # judged by setting one against the other. Observing the same card twice in
    # one instance is allowed too, because re-checking a mark that looked wrong
    # is data as well; whoever reads takes the latest by `observedAt`.
    "observations": {
        "indexes": [
            {"keys": [("instance", 1), ("source", 1), ("externalId", 1), ("observedAt", -1)],
             "name": "instance_source_externalId_observedAt", "unique": False},
            {"keys": [("instance", 1), ("observedAt", -1)], "name": "instance_observedAt", "unique": False},
        ],
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["instance", "set", "source", "externalId",
                             "schedule", "event", "place", "model", "observedAt"],
                "additionalProperties": False,
                "properties": {
                    "_id": {"bsonType": "objectId"},
                    # The xmemory instance the observer questioned, by its id.
                    "instance": {"bsonType": "string", "minLength": 1},
                    # The set the card was observed as part of.
                    "set": {"bsonType": "string", "pattern": NAME_PATTERN},
                    "source": {"bsonType": "string", "pattern": SOURCE_PATTERN},
                    "externalId": {"bsonType": "string"},
                    "schedule": MARK,
                    "event": MARK,
                    "place": MARK,
                    # What the observer asked memory, in its own words, one line each.
                    "asked": {"bsonType": "array", "items": {"bsonType": "string"}},
                    # One sentence on what would keep the worst of it from happening
                    # again; `null` when there was nothing to keep from happening.
                    "proposal": {"bsonType": ["string", "null"]},
                    # The model that observed: two marks are comparable only from the same.
                    "model": {"bsonType": "string", "minLength": 1},
                    # What the observation cost, in dollars and in seconds.
                    "costUsd": {"bsonType": ["double", "int"]},
                    "seconds": {"bsonType": ["int", "long", "double"]},
                    "observedAt": {"bsonType": "date"},
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
