"""The card — the contract between a parser and whatever receives its output.

Every parser, whatever it reads, produces cards of this shape and nothing else.
A card is one post: its identity in the source it came from, when it was
posted, and what it said. It carries no judgement about the post.

The fields:

    id      the post's id inside its own source, unique there
    source  where the post came from, as a path-safe name (`t.me/a_channel`)
    date    when it was posted, as an aware datetime in UTC
    text    the post as a reader sees it, links reduced to their anchor text
    links   the URLs behind those links, in the order they appeared

Dates are UTC, and a card refuses one without a time zone. A source states the
time in whatever zone suits it, and the parser converts before the card is
built — otherwise two parsers reading the same post disagree about when it
happened, and nothing downstream can tell which of them to believe.

Changing this shape changes every parser and every sink at once, so treat it as
an interface, not as a convenient place to hang a field.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone

# A source name is used to build a path, so it may only hold what a path
# tolerates: segments of word characters joined by `/`, and no `.` or `..`
# segment that could walk out of the directory it is given.
SEGMENT = r"(?!\.{1,2}(?:/|\Z))[\w.-]+"
SOURCE_NAME = re.compile(r"%s(?:/%s)*\Z" % (SEGMENT, SEGMENT))


@dataclass(frozen=True)
class Card:
    id: str
    source: str
    date: datetime
    text: str
    links: tuple = ()

    def __post_init__(self):
        if not self.id:
            raise ValueError("card has no id")
        if not SOURCE_NAME.match(self.source or ""):
            raise ValueError("not a usable source name: %r" % (self.source,))
        if not isinstance(self.date, datetime):
            raise ValueError("card date is not a datetime: %r" % (self.date,))
        if self.date.tzinfo is None or self.date.tzinfo.utcoffset(self.date) is None:
            raise ValueError("card %s of %s has a date with no time zone: %s" % (
                self.id, self.source, self.date))
        if not self.text.strip():
            raise ValueError("card %s of %s has no text" % (self.id, self.source))
        object.__setattr__(self, "id", str(self.id))
        object.__setattr__(self, "links", tuple(self.links))

    @property
    def day(self):
        """The UTC date the post belongs to, as `YYYY-MM-DD`."""
        return self.date.astimezone(timezone.utc).date().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "date": self.date.isoformat(),
            "text": self.text,
            "links": list(self.links),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            source=data["source"],
            date=datetime.fromisoformat(data["date"]),
            text=data["text"],
            links=tuple(data.get("links") or ()),
        )
