"""Which cards this run works on.

Answering 800 cards in one sitting is not a plan, so a run is given a slice of
the material to work through — a channel, a month, whatever the paths point at.
That choice is personal and changes between runs, so it lives in
`admin/config.json`, which git ignores. Copy `config.example.json` to it.

    {
      "cards": ["<a directory of card files>", "<another one>"],
      "port": 8765
    }

`cards` is required: a card file or a directory searched at any depth, either
absolute or relative to the repository. `port` is optional.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILE = os.path.join(REPO, "admin", "config.json")
DEFAULT_PORT = 8765


def read(path=DEFAULT_FILE):
    """The paths to work on and the port to listen on. Raises ValueError if unusable."""
    if not os.path.isfile(path):
        raise ValueError(
            "no configuration at %s: copy admin/config.example.json to it and say "
            "which cards to work on" % path)
    with open(path, encoding="utf-8") as fh:
        try:
            config = json.load(fh)
        except ValueError as error:
            raise ValueError("%s is not readable JSON: %s" % (path, error))

    paths = config.get("cards")
    if not paths or not isinstance(paths, list):
        raise ValueError("%s: `cards` must list at least one path" % path)
    resolved = [p if os.path.isabs(p) else os.path.join(REPO, p) for p in paths]
    for one in resolved:
        if not os.path.exists(one):
            raise ValueError("%s: no such path: %s" % (path, one))
    return resolved, int(config.get("port") or DEFAULT_PORT)
