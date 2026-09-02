"""Cards as files on disk: finding them and reading them back.

`JsonFileSink` writes one card per file; this reads those files into cards
again. The layout it wrote — a directory per source, then per day — is not
assumed here: any `.json` below a path is tried, and a file that is not a card
says so by name.
"""
import json
import os

from parsers.card import Card


def find(path):
    """Every card file at `path`, or anywhere below it, in a stable order."""
    if os.path.isfile(path):
        return [path]
    found = []
    for root, dirs, files in os.walk(path):
        dirs.sort()
        found.extend(os.path.join(root, name) for name in sorted(files) if name.endswith(".json"))
    return found


def read(paths):
    """Cards from every file under `paths`. Raises ValueError naming the first bad file."""
    cards = []
    for path in paths:
        for file_path in find(path):
            try:
                with open(file_path, encoding="utf-8") as fh:
                    cards.append(Card.from_dict(json.load(fh)))
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError("not a card: %s — %s" % (file_path, error))
    return cards
