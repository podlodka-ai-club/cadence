"""The cards being worked through, and what a decision does to them.

Two walks, and they are not the same walk. `Session` goes through cards that
have no answer yet and stops when they run out. `Review` goes back over the
answers already given, so every card it shows has one, and moving on changes
nothing by itself.

One run works through a fixed list of cards, read once at startup. A card the
database already has an answer about is not shown again — restarting picks up
where the last run stopped.

A skipped card is put aside for this run only: skipping says "not now", not
"no", and there is nothing to store about it. It comes back the next time the
panel is started.
"""


def key(card):
    return (card.source, card.id)


class Session:
    """One run of the panel over one set of cards."""

    def __init__(self, cards, answered):
        self.total = len(cards)
        self.pending = [card for card in cards if key(card) not in answered]
        self.skipped = []

    @property
    def current(self):
        return self.pending[0] if self.pending else None

    @property
    def progress(self):
        return {
            "answered": self.total - len(self.pending) - len(self.skipped),
            "skipped": len(self.skipped),
            "left": len(self.pending),
            "total": self.total,
        }

    def take(self, source, external_id):
        """The card at the front, if it is the one the page is talking about.

        The page and the panel can disagree — a reloaded page, a second window,
        a double press. Answering the wrong card silently would be worse than
        refusing, so the front of the queue has to match.
        """
        card = self.current
        if card is None or key(card) != (source, external_id):
            return None
        return card

    def skip(self, card):
        self.pending.remove(card)
        self.skipped.append(card)


class Review:
    """A walk back over the answers already given.

    The cards come from the database rather than from disk: an answer exists
    about a card that is already stored, and the point of this walk is to look
    at what was decided, not to find new material.

    The list is taken once, when the walk starts. A card answered afterwards
    joins it the next time the panel is started — a walk whose ground shifted
    underfoot would be worse than one that is a little behind.
    """

    def __init__(self, cards, answers):
        self.cards = cards
        self.answers = answers
        self.at = 0

    @property
    def current(self):
        return self.cards[self.at] if self.at < len(self.cards) else None

    @property
    def answer(self):
        card = self.current
        return self.answers.get(key(card)) if card else None

    @property
    def progress(self):
        return {
            "seen": self.at,
            "left": len(self.cards) - self.at,
            "total": len(self.cards),
        }

    def take(self, source, external_id):
        """The card the walk is on, if it is the one the page is talking about."""
        card = self.current
        if card is None or key(card) != (source, external_id):
            return None
        return card

    def replace(self, card, accept, reasons):
        self.answers[key(card)] = {"accept": accept, "reasons": list(reasons)}

    def move_on(self):
        self.at += 1

    def go_to(self, source, external_id):
        """Jump to one card, named by `(source, externalId)`. Returns whether it is
        in the walk; the walk stays where it was when it is not."""
        for index, card in enumerate(self.cards):
            if key(card) == (source, external_id):
                self.at = index
                return True
        return False

    def step_back(self):
        """Back to the card before this one, if there is one.

        Nothing is decided by stepping, so this asks for no card to agree with:
        it works at the end of the walk too, which is where a misplaced press
        is noticed.
        """
        self.at = max(0, self.at - 1)
