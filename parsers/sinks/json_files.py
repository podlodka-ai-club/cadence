"""A sink that writes each card as a JSON file on disk.

The path is derived from the card itself:

    <root>/<source>/<YYYY-MM-DD>/<id>.json

so a second run over the same posts overwrites the same files instead of
piling up duplicates, and a source stays browsable by day.
"""
import json
import os

from parsers.sinks.base import Sink


class JsonFileSink(Sink):
    """Writes cards under `root`. See the module docstring for the layout."""

    def __init__(self, root):
        self.root = root
        self.count = 0

    def path_for(self, card):
        return os.path.join(self.root, card.source, card.day, card.id + ".json")

    def send(self, card):
        path = self.path_for(card)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(card.to_dict(), fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        self.count += 1
        return path
