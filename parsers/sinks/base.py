"""What every sink is: something that accepts cards."""
import json
import sys


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


class PrintSink(Sink):
    """Writes each card to standard output, one JSON object per line.

    What a run that is only being looked at sends to: a channel read while
    somebody is developing against it, going nowhere but the terminal.
    """

    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self.count = 0

    def send(self, card):
        self.stream.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")
        self.stream.flush()
        self.count += 1
