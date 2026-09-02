"""The panel for answering cards by hand.

A card is shown, a person decides, the decision is written. Three parts:

    config.py   which cards this run works on
    session.py  the cards still waiting, and what happens to a decision
    server.py   the page and the requests behind it

Nothing here judges a card. The panel shows the post as it stands and stores
what the person said about it.
"""
