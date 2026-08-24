"""What every sink is: something that accepts cards."""


class Sink:
    """Receives cards one at a time. Subclasses decide where they land.

    `send` takes a single card. `close` runs once at the end, through the
    context manager, and is where a sink holding a connection or a batch
    flushes it; a sink that holds nothing leaves it alone.
    """

    def send(self, card):
        raise NotImplementedError

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class CountingSink(Sink):
    """Accepts cards and drops them. What a dry run sends to."""

    def __init__(self):
        self.count = 0

    def send(self, card):
        self.count += 1
